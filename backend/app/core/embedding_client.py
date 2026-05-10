"""Embedding abstraction — local sentence-transformers (v0) or OpenAI (v1)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Prefix required on the QUERY side when using BGE retrieval models.
# Documents (catalog, pitches) are embedded without a prefix.
_BGE_QUERY_PREFIX = (
    "Represent this sentence for searching relevant passages: "
)

# Lazy-loaded model cache for local embeddings
_local_model = None


def _get_local_model():
    """Load the sentence-transformers model lazily to avoid slow imports at startup."""
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading local embedding model: %s", settings.embedding_model_local)
        _local_model = SentenceTransformer(settings.embedding_model_local)
    return _local_model


async def embed_text_async(text: str, is_query: bool = False) -> list[float]:
    """Generate an embedding vector, offloaded to a thread so it doesn't block the event loop."""
    import asyncio
    return await asyncio.to_thread(embed_text, text, is_query)


def embed_text(text: str, is_query: bool = False) -> list[float]:
    """Generate an embedding vector for a single text string.

    Pass is_query=True when embedding a search query against a BGE model so the
    required retrieval prefix is applied.  Documents (catalog entries, pitches)
    should always use is_query=False (the default).
    """
    if settings.embedding_provider == "local":
        model = _get_local_model()
        if is_query and "bge" in settings.embedding_model_local.lower():
            text = _BGE_QUERY_PREFIX + text
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    elif settings.embedding_provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            model=settings.embedding_model_openai,
            input=text,
        )
        return response.data[0].embedding
    else:
        raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embedding vectors for multiple texts in batch."""
    if settings.embedding_provider == "local":
        model = _get_local_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
    elif settings.embedding_provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            model=settings.embedding_model_openai,
            input=texts,
        )
        return [item.embedding for item in response.data]
    else:
        raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
