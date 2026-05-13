"""Asset — an image uploaded by a user, referenced by templates."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # On-disk filename inside the assets volume. UUID-based, never the
    # user-supplied original name (see services.assets.save_image).
    storage_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width_px: Mapped[int] = mapped_column(Integer, nullable=False)
    height_px: Mapped[int] = mapped_column(Integer, nullable=False)

    # SHA-256 of the on-disk binary (hex). Used by template import to dedupe
    # an incoming asset against the user's existing uploads — same hash =
    # offer to reuse the existing Asset row instead of creating a duplicate.
    # Nullable for rows written before migration 0006; backfilled lazily.
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id} {self.original_filename} {self.size_bytes}B>"
