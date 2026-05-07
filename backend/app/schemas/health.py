"""Health API schemas."""

from datetime import datetime

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    status: str
    openai_api: bool
    database: bool
    timestamp: datetime
