"""Template — a label design owned by a user, with canvas tree as JSONB."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.asset import Asset  # noqa: F401 — FK target must be mapped first
from app.models.folder import Folder  # noqa: F401 — FK target must be mapped first
from app.models.label_format import LabelFormat
from app.models.user import User


def _utcnow() -> datetime:
    return datetime.now(UTC)


# JSONB on Postgres (rich querying + indexing) ↔ JSON-as-TEXT on SQLite (tests).
JsonField = JSON().with_variant(JSONB(), "postgresql")


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    format_id: Mapped[int] = mapped_column(
        ForeignKey("label_formats.id", ondelete="RESTRICT"), nullable=False
    )

    # Snapshot of dimensions at save time so the template stays renderable
    # even if a custom format is later deleted.
    width_mm: Mapped[float] = mapped_column(nullable=False)
    height_mm: Mapped[float] = mapped_column(nullable=False)

    # The Konva tree, serialized — schema lives in the frontend, backend
    # just persists it. Default is an empty stage.
    canvas_data: Mapped[dict[str, Any]] = mapped_column(JsonField, nullable=False)

    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Flat private folders — deleting a folder strands its templates back
    # into "no folder" rather than deleting them.
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Optional user-uploaded card thumbnail (featured image). Viewers of a
    # shared template read it through /api/templates/:id/featured-image,
    # which checks template access rather than asset ownership.
    featured_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    owner: Mapped[User] = relationship(lazy="joined")
    format: Mapped[LabelFormat] = relationship(lazy="joined")

    def __repr__(self) -> str:
        return f"<Template id={self.id} name={self.name!r} owner={self.owner_id}>"
