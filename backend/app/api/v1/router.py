"""API v1 router — includes all route modules."""

from fastapi import APIRouter

from app.api.v1.needs import router as needs_router

router = APIRouter(prefix="/api/v1")
router.include_router(needs_router)
