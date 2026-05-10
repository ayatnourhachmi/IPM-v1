"""API v1 router — includes all route modules."""

from fastapi import APIRouter

from app.core.config import settings
from app.api.v1.needs import router as needs_router

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def api_v1_health() -> dict[str, object]:
    """Same wiring summary as GET /health (for clients that only talk to /api/v1)."""
    return {
        "status": "healthy",
        "service": "ipm-api",
        "environment": settings.environment,
        "pinecone_api_key_present": bool(settings.pinecone_api_key.strip()),
        "pinecone_index_present": bool(settings.pinecone_index_name.strip()),
        "pinecone_configured": settings.pinecone_configured,
    }


router.include_router(needs_router)
