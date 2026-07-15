"""Runtime settings for the service layer."""

from __future__ import annotations

import os
from pathlib import Path

from saas_crawler.core.paths import CHECKPOINT_DIR, DATA_DIR


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://crawler:crawler@localhost:5432/saas_crawler",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CRAWLER_SECRET_KEY = os.getenv("CRAWLER_SECRET_KEY", "")
SERVICE_DATA_DIR = Path(os.getenv("DATA_DIR", str(DATA_DIR)))
SERVICE_CHECKPOINT_DIR = Path(os.getenv("CHECKPOINT_DIR", str(CHECKPOINT_DIR)))
AUTO_CREATE_TABLES = _bool_env("AUTO_CREATE_TABLES", default=False)
LOGIN_HEADLESS = _bool_env("LOGIN_HEADLESS", default=True)
LOGIN_TIMEOUT_SECONDS = int(os.getenv("LOGIN_TIMEOUT_SECONDS", "600"))
