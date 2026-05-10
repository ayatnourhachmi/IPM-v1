"""FastAPI application factory — CORS, lifespan, and router registration."""

from __future__ import annotations

import asyncio
import os
import logging
import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.database import engine
from app.models.business_need import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Columns added in Alembic 002/003; create_all() does not add new columns to existing tables.
_BN_OPTIONAL_JSONB_COLUMNS: tuple[str, ...] = (
    "constraints",
    "confidence",
    "risks",
    "justifications",
    "ivi_scores",
)


async def _ensure_business_needs_schema(async_conn) -> None:
    """Backfill JSONB columns when an older compose volume predates migrations."""
    res = await async_conn.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'business_needs')"
        )
    )
    if not res.scalar():
        return
    res2 = await async_conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'business_needs'"
        )
    )
    have = {row[0] for row in res2.fetchall()}
    for col in _BN_OPTIONAL_JSONB_COLUMNS:
        if col not in have:
            await async_conn.execute(
                text(f'ALTER TABLE business_needs ADD COLUMN "{col}" JSONB')
            )
            logger.info("Added missing column business_needs.%s (schema backfill)", col)


async def _run_post_startup_tasks() -> None:
    """Run heavy non-critical startup work without blocking API readiness."""
    # 1. Warm up embedding model (can be slow on first run due to model download)
    try:
        from app.core.embedding_client import _get_local_model

        await asyncio.to_thread(_get_local_model)
        logger.info("Embedding model warmed up.")
    except Exception as exc:
        logger.warning("Embedding model warmup failed (non-fatal): %s", exc)

    # 2. Seed ChromaDB with synthetic data
    try:
        from app.seeds.seed_chroma import seed_chromadb

        await asyncio.to_thread(seed_chromadb)
    except Exception as exc:
        logger.warning("ChromaDB seeding failed (non-fatal): %s", exc)

    # 3. Seed DXC product catalog into dxc_catalog collection
    try:
        from app.core.seed_catalog import seed_catalog

        await asyncio.to_thread(seed_catalog)
    except Exception as exc:
        logger.warning("Catalog seeding failed (non-fatal): %s", exc)

    # 4. Ensure MinIO bucket exists
    try:
        from app.core.minio_client import ensure_bucket

        await asyncio.to_thread(ensure_bucket)
        logger.info("MinIO bucket ensured.")
    except Exception as exc:
        logger.warning("MinIO bucket creation failed (non-fatal): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle events."""
    logger.info("Starting IPM API...")

    # 1. Create missing tables; does not ALTER existing tables when new columns are added to models.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Backfill columns on long-lived dev DBs (docker volume) that predate Alembic 002/003.
    async with engine.begin() as conn:
        await _ensure_business_needs_schema(conn)

    logger.info("Database tables ensured.")

    # Run heavy non-critical startup work in background.
    asyncio.create_task(_run_post_startup_tasks())

    logger.info("IPM API ready.")
    yield

    # Shutdown
    await engine.dispose()
    logger.info("IPM API shutdown complete.")


app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan,
)

# --- CORS ---
allow_origin_regex = os.getenv("CORS_ORIGIN_REGEX")
if not allow_origin_regex and settings.environment == "production":
    allow_origin_regex = r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=allow_origin_regex,
)

# --- Routes ---
app.include_router(api_v1_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return a simple health status."""
    return {"status": "healthy", "service": "ipm-api"}
