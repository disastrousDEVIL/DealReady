"""Expire demo links and delete their OpenAI vector stores.

Run with:
    python -m app.jobs.expire_demos
"""

import json
from typing import Any

from app.db.session import SessionLocal
from app.services.demo_lifecycle_service import DemoLifecycleService


def run_expiry() -> dict[str, Any]:
    with SessionLocal() as db:
        return DemoLifecycleService(db=db).expire_due_demos()


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda handler for EventBridge scheduled cleanup."""
    result = run_expiry()
    return {
        "statusCode": 200,
        "body": json.dumps(result),
    }


def main() -> None:
    result = run_expiry()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
