"""Redis-backed batch-PDF job state.

For the MVP cap of 1000 rows we run jobs in a background thread inside the
Gunicorn worker. The job's lifecycle (status / progress / output path) is
stored in Redis so polling works across worker processes and the PDF itself
lives on the pdfs volume — same approach as uploaded assets.

If we later outgrow this and need cross-host workers, swap the executor for
Celery without changing the Redis keys.
"""

from __future__ import annotations

import enum
import json
import os
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import redis

KEY_PREFIX = "blg:job:"
TTL_SECONDS = 60 * 60 * 24  # 24 h


class JobStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


def pdfs_dir() -> Path:
    return Path(os.environ.get("PDFS_DIR", "/app/pdfs"))


def _redis_client(redis_url: str) -> redis.Redis[bytes]:
    return redis.Redis.from_url(redis_url)


def _key(job_id: str) -> str:
    return f"{KEY_PREFIX}{job_id}"


def _serialize(state: dict[str, Any]) -> bytes:
    return json.dumps(state).encode()


def _deserialize(raw: bytes | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    return json.loads(raw)  # type: ignore[no-any-return]


def create_job(
    redis_url: str,
    *,
    owner_id: int,
    template_id: int,
    total: int,
) -> str:
    """Create a fresh job and return its id. Status starts at PENDING."""
    job_id = uuid.uuid4().hex
    state = {
        "id": job_id,
        "owner_id": owner_id,
        "template_id": template_id,
        "status": JobStatus.PENDING.value,
        "progress": 0,
        "total": total,
        "pdf_path": None,
        "error": None,
        "warnings": [],
    }
    _redis_client(redis_url).setex(_key(job_id), TTL_SECONDS, _serialize(state))
    return job_id


def get_job(redis_url: str, job_id: str) -> dict[str, Any] | None:
    raw = _redis_client(redis_url).get(_key(job_id))
    return _deserialize(raw)


def _update(redis_url: str, job_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    client = _redis_client(redis_url)
    raw = client.get(_key(job_id))
    state = _deserialize(raw)
    if state is None:
        return None
    state.update(patch)
    client.setex(_key(job_id), TTL_SECONDS, _serialize(state))
    return state


def run_in_thread(
    redis_url: str,
    job_id: str,
    *,
    runner: Callable[[Callable[[int, int], None], list[dict[str, Any]]], bytes],
    output_filename: str,
) -> None:
    """Spawn a daemon thread that runs `runner`, writes its output bytes to
    pdfs_dir(), and updates the job state along the way. `runner` is a
    closure that takes a progress callback `(done, total) -> None` and a
    `warnings` list it appends soft-failure entries to (e.g. text-block
    overflows)."""

    def _worker() -> None:
        _update(redis_url, job_id, {"status": JobStatus.RUNNING.value})

        def _progress(done: int, total: int) -> None:
            _update(redis_url, job_id, {"progress": done, "total": total})

        warnings: list[dict[str, Any]] = []
        try:
            pdf_bytes = runner(_progress, warnings)
        except Exception as exc:  # noqa: BLE001
            _update(
                redis_url,
                job_id,
                {"status": JobStatus.ERROR.value, "error": str(exc)},
            )
            return

        pdfs_dir().mkdir(parents=True, exist_ok=True)
        target = pdfs_dir() / output_filename
        target.write_bytes(pdf_bytes)

        _update(
            redis_url,
            job_id,
            {
                "status": JobStatus.DONE.value,
                "pdf_path": str(target.name),
                "warnings": warnings,
            },
        )

    threading.Thread(target=_worker, daemon=True).start()
