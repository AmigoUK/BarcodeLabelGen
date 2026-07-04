"""Record of a generated file (single label, batch PDF, batch ZPL) — F18.

The bytes live on the pdfs volume; this row is the durable index the
History page reads, and survives the Redis job record's 24h expiry.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class GeneratedFile(Base):
    __tablename__ = "generated_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # History outlives the source template — snapshot the name, null the FK.
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("templates.id", ondelete="SET NULL"), nullable=True
    )
    template_name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)  # "pdf" | "zpl"
    mode: Mapped[str] = mapped_column(String(8), nullable=False)  # "single" | "series"
    storage_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<GeneratedFile id={self.id} {self.kind}/{self.mode} owner={self.owner_id}>"
