"""Embedding service — embed, upsert, and search business needs in ChromaDB."""

from __future__ import annotations

import logging

from app.core.chroma import get_collection
from app.core.embedding_client import embed_text
from app.schemas.business_need import DuplicateMatch

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.80
MAX_RESULTS = 3


def upsert_embedding(need_id: str, pitch: str, status: str, embedding: list[float] | None = None) -> None:
    """Upsert a pitch embedding into ChromaDB. Computes the embedding if not provided."""
    if embedding is None:
        embedding = embed_text(pitch, is_query=False)
    collection = get_collection()
    collection.upsert(
        ids=[need_id],
        embeddings=[embedding],
        documents=[pitch],
        metadatas=[{"status": status}],
    )
    logger.info("Upserted embedding for %s into ChromaDB", need_id)


def search_duplicates(pitch: str, exclude_id: str | None = None, embedding: list[float] | None = None) -> list[DuplicateMatch]:
    """Search ChromaDB for business needs similar to the given pitch. Reuses embedding if provided."""
    if embedding is None:
        embedding = embed_text(pitch, is_query=False)
    collection = get_collection()

    # Query more results than needed to account for excluding self
    n_results = MAX_RESULTS + (1 if exclude_id else 0)
    total = collection.count()
    if total == 0:
        return []
    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(n_results, total),
        include=["documents", "metadatas", "distances"],
    )

    if not results or not results["ids"] or not results["ids"][0]:
        return []

    matches: list[DuplicateMatch] = []
    for i, doc_id in enumerate(results["ids"][0]):
        if doc_id == exclude_id:
            continue

        # ChromaDB returns cosine distance; similarity = 1 - distance
        distance = results["distances"][0][i] if results["distances"] else 1.0
        similarity = 1.0 - distance

        if similarity >= SIMILARITY_THRESHOLD:
            matches.append(
                DuplicateMatch(
                    id=doc_id,
                    pitch=results["documents"][0][i] if results["documents"] else "",
                    status=results["metadatas"][0][i].get("status", "unknown") if results["metadatas"] else "unknown",
                    similarity_score=round(similarity, 4),
                )
            )

        if len(matches) >= MAX_RESULTS:
            break

    return matches
