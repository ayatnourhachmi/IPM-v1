"""Embedding service — embed, upsert, and search business needs in Pinecone."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.embedding_client import embed_text
from app.core.pinecone_store import NS_BUSINESS_NEEDS, query_similar_needs, upsert_need_vectors
from app.schemas.business_need import DuplicateMatch

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.80
MAX_RESULTS = 3


def upsert_embedding(need_id: str, pitch: str, status: str, embedding: list[float] | None = None) -> None:
    """Upsert a pitch embedding into Pinecone ``business_needs`` namespace."""
    if not settings.pinecone_configured:
        logger.info("Pinecone not configured — skipping upsert for %s", need_id)
        return
    if embedding is None:
        embedding = embed_text(pitch, is_query=False)

    upsert_need_vectors(
        [
            {
                "id": need_id,
                "values": embedding,
                "metadata": {"pitch": pitch, "status": str(status)},
            }
        ]
    )
    logger.info("Upserted embedding for %s into Pinecone/%s", need_id, NS_BUSINESS_NEEDS)


def search_duplicates(
    pitch: str,
    exclude_id: str | None = None,
    embedding: list[float] | None = None,
) -> list[DuplicateMatch]:
    """Find similar business needs in Pinecone (cosine similarity ≥ threshold)."""
    if not settings.pinecone_configured:
        return []

    if embedding is None:
        embedding = embed_text(pitch, is_query=False)

    fetch_k = max(MAX_RESULTS + 2, MAX_RESULTS + (2 if exclude_id else 1))
    rows = query_similar_needs(embedding, top_k=fetch_k, exclude_id=exclude_id)

    matches: list[DuplicateMatch] = []
    for doc_id, similarity, _meta, pitch_text in rows:
        if similarity >= SIMILARITY_THRESHOLD:
            matches.append(
                DuplicateMatch(
                    id=doc_id,
                    pitch=pitch_text or "",
                    status=str(_meta.get("status", "unknown")),
                    similarity_score=round(similarity, 4),
                )
            )

        if len(matches) >= MAX_RESULTS:
            break

    return matches
