"""Application configuration helpers."""

import os
from dotenv import load_dotenv

load_dotenv(".env")


def get_database_url() -> str:
    """Return database URL from environment."""
    return os.getenv("DATABASE_URL", "")


def is_database_configured() -> bool:
    """Validate database URL format expected by this project."""
    return get_database_url().startswith("postgresql+psycopg://")
