"""ChromaDB HTTP client singleton."""

from __future__ import annotations

import chromadb

from app.core.config import settings

_client: chromadb.HttpClient | None = None
_collections: dict[str, chromadb.Collection] = {}


def get_chroma_client() -> chromadb.HttpClient:
    """Return the singleton ChromaDB HTTP client."""
    global _client
    if _client is None:
        _client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
    return _client


def get_collection(name: str = "business_needs") -> chromadb.Collection:
    """Return a ChromaDB collection by name, creating it if needed."""
    global _collections
    if name not in _collections:
        client = get_chroma_client()
        _collections[name] = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
    return _collections[name]
