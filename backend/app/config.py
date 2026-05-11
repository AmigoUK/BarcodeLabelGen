"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    database_url: str
    redis_url: str
    flask_env: str
    secret_key: str

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            database_url=os.environ.get("DATABASE_URL", "postgresql://blg:blg@db:5432/blg"),
            redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
            flask_env=os.environ.get("FLASK_ENV", "production"),
            secret_key=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        )
