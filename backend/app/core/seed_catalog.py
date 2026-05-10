"""Seed the DXC product catalog into a dedicated ChromaDB collection.

Runs once at startup via the lifespan hook in main.py.
Uses upsert so the metadata schema stays current across restarts.
"""

from __future__ import annotations

import logging
from app.services.catalog_loader import catalog_loader, Solution
from app.core.chroma import get_collection
from app.core.embedding_client import embed_text

logger = logging.getLogger(__name__)
_COLLECTION_NAME = "dxc_catalog"


def _build_document(solution: Solution) -> str:
    """Build the text document used for embedding and full-text retrieval."""
    parts = [
        f"{solution.solution_name}.",
        (solution.description or "") + ".",
    ]
    if solution.features:
        parts.append(f"Features: {', '.join(solution.features)}.")
    return " ".join(p for p in parts if p and p != ".")


def _build_metadata(solution: Solution) -> dict:
    """Build flat ChromaDB metadata from a Solution object.

    All list fields are serialised as comma-separated strings because
    ChromaDB metadata values must be scalar (str | int | float | bool).
    """
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
    """Load Excel-based catalog into the dxc_catalog ChromaDB collection.

    Always upserts so metadata stays in sync with the Excel file.
    Embeddings are recomputed only when a solution's document text changes.
    """
    solutions = catalog_loader.get_solutions()
    if not solutions:
        logger.warning("Catalog loader returned no solutions — skipping seed")
        return

    collection = get_collection(_COLLECTION_NAME)
    inserted = 0

    for idx, solution in enumerate(solutions):
        pid = f"EXCEL-{idx + 1}"
        document = _build_document(solution)
        embedding = embed_text(document, is_query=False)
        metadata = _build_metadata(solution)
        collection.upsert(
            ids=[pid],
            embeddings=[embedding],
            documents=[document],
            metadatas=[metadata],
        )
        inserted += 1

    logger.info(
        "Catalog seeding complete: %d solutions upserted into '%s'",
        inserted,
        _COLLECTION_NAME,
    )
