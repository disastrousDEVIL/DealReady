"""V1 API router."""

from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.workspaces import router as workspaces_router

router = APIRouter(prefix="/api/v1")
router.include_router(workspaces_router)
router.include_router(health_router)
