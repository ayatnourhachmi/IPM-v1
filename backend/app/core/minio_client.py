"""MinIO S3-compatible client singleton — ready for Phase 2 document storage."""

from __future__ import annotations

from minio import Minio

from app.core.config import settings

_client: Minio | None = None


def get_minio_client() -> Minio:
    """Return the singleton MinIO client."""
    global _client
    if _client is None:
        _client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def ensure_bucket(bucket_name: str = "ipm-documents") -> None:
    """Create the default bucket if it does not exist."""
    client = get_minio_client()
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
