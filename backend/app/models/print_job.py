"""Print queue for the local connector — one row per ZPL job for a device.

Lifecycle: pending → sent (agent fetched it) → done | error (agent report).
The ZPL is stored fully resolved (dates already substituted), so the agent
never interprets placeholders.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PrintJobStatus(enum.StrEnum):
    PENDING = "pending"
    SENT = "sent"
    DONE = "done"
    ERROR = "error"


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    printer: Mapped[str] = mapped_column(String(100), nullable=False)
    copies: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    zpl: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PrintJobStatus] = mapped_column(
        Enum(
            PrintJobStatus,
            name="print_job_status",
            values_callable=lambda e: [s.value for s in e],
        ),
        nullable=False,
        default=PrintJobStatus.PENDING,
        index=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PrintJob id={self.id} device={self.device_id} status={self.status}>"
