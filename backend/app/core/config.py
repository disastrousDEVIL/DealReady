"""Application configuration helpers."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_database_url() -> str:
    """Return database URL from environment."""
    return os.getenv("DATABASE_URL", "")


def is_database_configured() -> bool:
    """Validate database URL format expected by this project."""
    return get_database_url().startswith("postgresql+psycopg://")
