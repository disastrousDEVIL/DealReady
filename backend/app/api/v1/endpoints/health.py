"""Health endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends

from app.api.deps import get_vector_store_service
from app.core.config import is_database_configured
from app.schemas.workspace import HealthCheckResponse
from app.services.vector_store_service import VectorStoreService

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthCheckResponse)
async def health_check(service: VectorStoreService = Depends(get_vector_store_service)):
    openai_ok = service.health_check()
    db_ok = is_database_configured()
    status = "healthy" if (openai_ok and db_ok) else "unhealthy"
    return HealthCheckResponse(
        status=status,
        openai_api=openai_ok,
        database=db_ok,
        timestamp=datetime.utcnow(),
    )
