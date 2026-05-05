"""Shared API dependencies."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.vector_store_service import VectorStoreService


def get_vector_store_service() -> VectorStoreService:
    return VectorStoreService()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
