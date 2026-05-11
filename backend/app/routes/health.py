"""Health check endpoint — verifies DB and Redis reachability."""

from __future__ import annotations

import logging

import psycopg
import redis
from flask import Blueprint, Response, current_app, jsonify

from app.config import Config

log = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)


def _check_db(database_url: str) -> tuple[bool, str | None]:
    # psycopg.connect doesn't understand SQLAlchemy's `+driver` URL suffix.
    raw_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    try:
        with psycopg.connect(raw_url, connect_timeout=2) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception as exc:  # noqa: BLE001 — broad except is intentional for health probe
        log.warning("DB health check failed: %s", exc)
        return False, str(exc)
    return True, None


def _check_redis(redis_url: str) -> tuple[bool, str | None]:
    try:
        client = redis.Redis.from_url(redis_url, socket_connect_timeout=2)
        client.ping()
    except Exception as exc:  # noqa: BLE001
        log.warning("Redis health check failed: %s", exc)
        return False, str(exc)
    return True, None


@health_bp.get("/health")
def health() -> tuple[Response, int]:
    cfg: Config = current_app.config["APP_CONFIG"]

    db_ok, db_err = _check_db(cfg.database_url)
    redis_ok, redis_err = _check_redis(cfg.redis_url)

    payload = {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "service": "barcodelabelgen-backend",
        "version": "0.1.0",
        "checks": {
            "database": {"ok": db_ok, "error": db_err},
            "redis": {"ok": redis_ok, "error": redis_err},
        },
    }
    http_status = 200 if (db_ok and redis_ok) else 503
    return jsonify(payload), http_status
