"""Pinecone vector store — business need embeddings + DXC catalog (namespaces).

Replaces ChromaDB. Requires a serverless (or compatible) Pinecone index with cosine metric.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from pinecone import Pinecone, ServerlessSpec

from app.core.config import settings

logger = logging.getLogger(__name__)

NS_BUSINESS_NEEDS = "business_needs"
NS_DXC_CATALOG = "dxc_catalog"

_META_PITCH_CAP = 12_000
_META_DOC_CAP = 40_000

_pc: Pinecone | None = None
_index: Any | None = None


def _get_pc() -> Pinecone:
    global _pc
    if _pc is None:
        if not settings.pinecone_api_key.strip():
            raise RuntimeError("PINECONE_API_KEY is not set")
        _pc = Pinecone(api_key=settings.pinecone_api_key)
    return _pc


def _sanitize_meta_key(k: object) -> str:
    raw = "".join((c if c.isalnum() or c == "_" else "_") for c in str(k).strip())
    return (raw.strip("_") or "k")[:64]


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Pinecone metadata: scalar str / int / float / bool only (omit nulls)."""
    out: dict[str, Any] = {}
    for k, v in metadata.items():
        if v is None:
            continue
        key = _sanitize_meta_key(k)
        if isinstance(v, bool):
            out[key] = v
        elif isinstance(v, int) and not isinstance(v, bool):
            out[key] = v
        elif isinstance(v, float):
            out[key] = float(v)
        elif isinstance(v, str):
            lim = _META_PITCH_CAP if key == "pitch" else _META_DOC_CAP
            out[key] = v[:lim]
        else:
            out[key] = str(v)[:_META_DOC_CAP]
    return out


def ensure_pinecone_index_ready() -> None:
    """Create the index when configured to auto-create; otherwise verify it exists."""
    if not settings.pinecone_configured:
        return

    pc = _get_pc()
    name = settings.pinecone_index_name
    idx_names = list(pc.list_indexes().names())

    if name in idx_names:
        return

    if not settings.pinecone_auto_create_index:
        raise RuntimeError(
            f"Pinecone index {name!r} was not found. Create a serverless index with "
            f"metric=cosine, dimension={settings.pinecone_index_dimension}, "
            "or set PINECONE_AUTO_CREATE_INDEX=true."
        )

    logger.info(
        "Creating Pinecone serverless index %r (dim=%s, cosine)...",
        name,
        settings.pinecone_index_dimension,
    )
    pc.create_index(
        name=name,
        dimension=int(settings.pinecone_index_dimension),
        metric="cosine",
        spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
    )

    deadline = time.time() + 300
    while time.time() < deadline:
        desc = pc.describe_index(name)
        ready = getattr(getattr(desc, "status", None), "ready", False)
        if ready:
            logger.info("Pinecone index %r is ready.", name)
            return
        time.sleep(2)

    raise RuntimeError(f"Timed out waiting for Pinecone index {name!r} to become ready.")


def get_pinecone_index():
    """Return cached Index handle; ensures index existence policy on first access."""
    if not settings.pinecone_configured:
        raise RuntimeError("Pinecone is not configured — set PINECONE_API_KEY and PINECONE_INDEX.")
    global _index
    if _index is None:
        ensure_pinecone_index_ready()
        _index = _get_pc().Index(settings.pinecone_index_name)
    return _index


def invalidate_index_connection() -> None:
    """Reset cached client/index (tests or key rotation)."""
    global _pc, _index
    _pc = None
    _index = None


def namespace_vector_count(namespace: str) -> int:
    if not settings.pinecone_configured:
        return 0
    stats = get_pinecone_index().describe_index_stats()
    ns_map = getattr(stats, "namespaces", None)
    if ns_map is None:
        return 0
    # SDK may expose dict-like or protobuf map
    if hasattr(ns_map, "get"):
        entry = ns_map.get(namespace)
    else:
        entry = getattr(ns_map, namespace, None)
    if entry is None:
        return 0
    vc = getattr(entry, "vector_count", None)
    if vc is not None:
        return int(vc)
    try:
        return int(entry["vector_count"])
    except Exception:
        return 0


def upsert_need_vectors(vectors: list[dict[str, Any]]) -> None:
    if not settings.pinecone_configured:
        logger.info("Pinecone not configured — skipping need vector upsert")
        return

    cleaned: list[dict[str, Any]] = []
    for row in vectors:
        meta_raw = dict(row.get("metadata") or {})
        cleaned.append(
            {
                "id": row["id"],
                "values": row["values"],
                "metadata": _clean_metadata(meta_raw),
            }
        )

    idx = get_pinecone_index()
    idx.upsert(vectors=cleaned, namespace=NS_BUSINESS_NEEDS)


def upsert_catalog_vectors(vectors: list[dict[str, Any]], batch_size: int = 96) -> None:
    if not settings.pinecone_configured:
        logger.info("Pinecone not configured — skipping catalog upsert")
        return

    idx = get_pinecone_index()
    for i in range(0, len(vectors), batch_size):
        chunk = vectors[i : i + batch_size]
        cleaned = [
            {"id": r["id"], "values": r["values"], "metadata": _clean_metadata(dict(r.get("metadata") or {}))}
            for r in chunk
        ]
        idx.upsert(vectors=cleaned, namespace=NS_DXC_CATALOG)


def query_similar_needs(
    embedding: list[float],
    *,
    top_k: int,
    exclude_id: str | None,
) -> list[tuple[str, float, dict[str, Any], str]]:
    """Return tuples (id, similarity_score, metadata, pitch_text)."""
    if not settings.pinecone_configured:
        return []
    if namespace_vector_count(NS_BUSINESS_NEEDS) <= 0:
        return []

    idx = get_pinecone_index()
    top_k_eff = max(2, top_k)
    resp = idx.query(
        vector=embedding,
        top_k=top_k_eff,
        namespace=NS_BUSINESS_NEEDS,
        include_metadata=True,
    )
    matches = getattr(resp, "matches", None) or []
    rows: list[tuple[str, float, dict[str, Any], str]] = []
    for m in matches:
        mid = str(getattr(m, "id", "") or "")
        if exclude_id and mid == exclude_id:
            continue
        score = float(getattr(m, "score", 0.0) or 0.0)
        raw_meta = getattr(m, "metadata", None)
        meta = dict(raw_meta or {})
        pitch = str(meta.get("pitch", "") or "")
        rows.append((mid, score, meta, pitch))
    return rows


def query_catalog(
    embedding: list[float],
    *,
    top_k: int,
) -> list[tuple[str, dict[str, Any], str, float]]:
    """Return tuples (catalog_row_id, metadata, document_body, cosine_similarity)."""
    if not settings.pinecone_configured:
        return []
    if namespace_vector_count(NS_DXC_CATALOG) <= 0:
        return []

    idx = get_pinecone_index()
    top_k_eff = max(2, top_k)
    resp = idx.query(
        vector=embedding,
        top_k=top_k_eff,
        namespace=NS_DXC_CATALOG,
        include_metadata=True,
    )
    matches = getattr(resp, "matches", None) or []
    rows: list[tuple[str, dict[str, Any], str, float]] = []
    for m in matches:
        mid = str(getattr(m, "id", "") or "")
        score = float(getattr(m, "score", 0.0) or 0.0)
        raw_meta = getattr(m, "metadata", None)
        meta = dict(raw_meta or {})
        doc = str(meta.get("document", "") or "")
        rows.append((mid, meta, doc, score))
    return rows
