"""Seed the DXC product catalog into the Pinecone ``dxc_catalog`` namespace.

Runs on startup in development, and in production when ``pinecone_seed_catalog_on_startup`` is true.
Upserts are idempotent (same ids / Excel row order).
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.embedding_client import embed_text
from app.core.pinecone_store import ensure_pinecone_index_ready, upsert_catalog_vectors
from app.services.catalog_loader import catalog_loader, Solution

logger = logging.getLogger(__name__)


def _build_document(solution: Solution) -> str:
    """Build the text document used for embedding and retrieval."""
    parts = [
        f"{solution.solution_name}.",
        (solution.description or "") + ".",
    ]
    if solution.features:
        parts.append(f"Features: {', '.join(solution.features)}.")
    return " ".join(p for p in parts if p and p != ".")


def _build_metadata(solution: Solution) -> dict:
    """Scalar metadata compatible with Pinecone (lists stored as comma-separated strings)."""
    return {
        "name": solution.solution_name,
        "domain": solution.domain or "",
        "maturity": solution.maturity or "",
        "target_objective": solution.target_objective or "",
        "client_sectors": ", ".join(solution.client_sectors),
        "complexity": solution.complexity or "",
        "ipm_stage": solution.ipm_stage or "",
        "features": ", ".join(solution.features),
        "limitations": ", ".join(solution.limitations),
        "deployments": solution.deployments,
    }


def seed_catalog() -> None:
    """Load Excel catalog into Pinecone ``dxc_catalog`` namespace."""
    if not settings.pinecone_configured:
        logger.warning("Pinecone not configured — skip catalog seed")
        return

    ensure_pinecone_index_ready()

    solutions = catalog_loader.get_solutions()
    if not solutions:
        logger.warning("Catalog loader returned no solutions — skipping seed")
        return

    vectors: list[dict] = []
    for idx, solution in enumerate(solutions):
        pid = f"EXCEL-{idx + 1}"
        document = _build_document(solution)
        embedding = embed_text(document, is_query=False)
        metadata = _build_metadata(solution)
        metadata["document"] = document
        vectors.append({"id": pid, "values": embedding, "metadata": metadata})

    upsert_catalog_vectors(vectors)

    logger.info(
        "Catalog seeding complete: %d solutions upserted into Pinecone dxc_catalog namespace",
        len(vectors),
    )
