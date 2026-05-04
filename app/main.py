"""Application entrypoint."""

import logging
from fastapi import FastAPI

from app.core import config as _config  # noqa: F401
from app.api.v1.router import router as api_v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title="InstaRAG Backend")
app.include_router(api_v1_router)
