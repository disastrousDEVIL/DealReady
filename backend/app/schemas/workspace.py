"""Workspace API schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.workspace import FileStatus


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    owner_id: str


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    owner_id: str
    vector_store_id: str
    description: Optional[str] = None
    file_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class WorkspaceFileResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    file_id: str
    original_name: str
    file_type: str
    size_bytes: Optional[int] = None
    status: FileStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(from_attributes=True)


class QueryRequest(BaseModel):
    question: str
    max_results: int = 10
    include_search_results: bool = False


class QueryResponse(BaseModel):
    answer: str
    citations: list[dict[str, str]] = []
    search_results: list[dict[str, Any]] = []
    usage: dict[str, int]


class AgentQueryResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]] = []
    usage: dict[str, Any] = {}
    tool_calls: list[dict[str, Any]] = []


class ResponsesQueryRequest(QueryRequest):
    previous_response_id: Optional[str] = None
    store: bool = True


class ResponsesQueryResponse(AgentQueryResponse):
    response_id: str
    previous_response_id: Optional[str] = None


class HealthCheckResponse(BaseModel):
    status: str
    openai_api: bool
    database: bool
    timestamp: datetime
