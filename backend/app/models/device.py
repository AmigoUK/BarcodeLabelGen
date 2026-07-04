"""Connector devices — local print agents authenticated by a per-device token.

The plaintext token is shown once at creation; only its SHA-256 hex digest
is stored, so a leaked database dump can't be replayed against the API.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

JsonField = JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("owner_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    agent_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Printers the agent reported: [{"name": ..., "host": ..., "port": ...}, ...]
    printers: Mapped[list[Any]] = mapped_column(JsonField, nullable=False, default=list)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Device id={self.id} name={self.name!r} owner={self.owner_id}>"
