"""Workspace-related ORM models."""

from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class FileStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkspaceORM(Base):
    __tablename__ = "instarag_workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(String(255), nullable=False)
    vector_store_id = Column(String(255), nullable=False, unique=True)
    description = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class WorkspaceFileORM(Base):
    __tablename__ = "instarag_workspace_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("instarag_workspaces.id"), nullable=False)
    file_id = Column(String(255), nullable=False, unique=True)
    vector_store_file_id = Column(String(255), nullable=False, unique=True)
    original_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    size_bytes = Column(Integer, nullable=True)
    status = Column(SQLEnum(FileStatus), default=FileStatus.PROCESSING)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatSessionORM(Base):
    __tablename__ = "instarag_chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("instarag_workspaces.id"), nullable=False)
    user_id = Column(String(255), nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessageORM(Base):
    __tablename__ = "instarag_chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("instarag_chat_sessions.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(String(8192), nullable=False)
    citations = Column(String(4096), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
