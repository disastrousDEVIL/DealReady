"""Demo chatbot API schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.demo import DemoStatus


class DemoResponse(BaseModel):
    id: UUID
    prospect_name: str
    company_url: str
    logo_url: Optional[str] = None
    public_slug: str
    chat_url: str
    status: DemoStatus
    expires_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DemoCreateResponse(DemoResponse):
    vector_store_id: str
    generated_password: str
    indexed_files: list[dict[str, Any]] = []
    pages_crawled: int = 0


class DemoQueryRequest(BaseModel):
    question: str
    previous_response_id: Optional[str] = None
    max_results: int = 10
    store: bool = True
    access_password: Optional[str] = None


class DemoAuthRequest(BaseModel):
    access_password: Optional[str] = None


class DemoAuthResponse(BaseModel):
    authenticated: bool
    requires_password: bool


class DemoQueryResponse(BaseModel):
    answer: str
    response_id: str
    previous_response_id: Optional[str] = None
    citations: list[dict[str, Any]] = []
    usage: dict[str, Any] = {}
    tool_calls: list[dict[str, Any]] = []
