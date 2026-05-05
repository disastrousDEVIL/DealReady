"""Demo chatbot ORM models."""

from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class DemoStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"


class DemoFileStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class AgentDemoORM(Base):
    __tablename__ = "instarag_agent_demos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    prospect_name = Column(String(255), nullable=False)
    company_url = Column(String(1024), nullable=False)
    logo_url = Column(String(1024), nullable=True)
    vector_store_id = Column(String(255), nullable=False, unique=True)
    public_slug = Column(String(255), nullable=False, unique=True)
    access_password = Column(String(255), nullable=True)
    status = Column(SQLEnum(DemoStatus), nullable=False, default=DemoStatus.ACTIVE)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentDemoFileORM(Base):
    __tablename__ = "instarag_agent_demo_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    demo_id = Column(UUID(as_uuid=True), ForeignKey("instarag_agent_demos.id"), nullable=False)
    file_id = Column(String(255), nullable=False, unique=True)
    vector_store_file_id = Column(String(255), nullable=False, unique=True)
    original_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    source_url = Column(String(2048), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    status = Column(SQLEnum(DemoFileStatus), nullable=False, default=DemoFileStatus.COMPLETED)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
