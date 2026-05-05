"""Lifecycle cleanup for expiring demo chatbot links."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.demo import AgentDemoORM, DemoStatus
from app.services.vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)


class DemoLifecycleService:
    """Expires demo links and deletes their OpenAI vector stores."""

    def __init__(self, db: Session, vector_service: VectorStoreService | None = None) -> None:
        self.db = db
        self.vector_service = vector_service or VectorStoreService()

    def expire_due_demos(self, now: datetime | None = None) -> Dict[str, Any]:
        now = now or datetime.utcnow()
        demos = (
            self.db.query(AgentDemoORM)
            .filter(AgentDemoORM.status == DemoStatus.ACTIVE, AgentDemoORM.expires_at <= now)
            .all()
        )

        expired: List[Dict[str, Any]] = []
        failed: List[Dict[str, Any]] = []

        for demo in demos:
            try:
                self.vector_service.delete_workspace_vector_store(demo.vector_store_id)
                vector_store_deleted = True
            except Exception as exc:
                logger.warning(
                    "failed_to_delete_expired_demo_vector_store demo_id=%s vector_store_id=%s error=%s",
                    demo.id,
                    demo.vector_store_id,
                    exc,
                )
                vector_store_deleted = False
                failed.append(
                    {
                        "demo_id": str(demo.id),
                        "public_slug": demo.public_slug,
                        "vector_store_id": demo.vector_store_id,
                        "error": str(exc),
                    }
                )

            demo.status = DemoStatus.EXPIRED
            expired.append(
                {
                    "demo_id": str(demo.id),
                    "public_slug": demo.public_slug,
                    "vector_store_id": demo.vector_store_id,
                    "vector_store_deleted": vector_store_deleted,
                }
            )

        self.db.commit()
        return {
            "expired_count": len(expired),
            "failed_delete_count": len(failed),
            "expired": expired,
            "failed": failed,
        }
