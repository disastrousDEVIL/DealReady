"""V1 API router."""

from fastapi import APIRouter

from app.api.v1.endpoints.demos import router as demos_router
from app.api.v1.endpoints.health import router as health_router

router = APIRouter(prefix="/api/v1")
router.include_router(demos_router)
router.include_router(health_router)
