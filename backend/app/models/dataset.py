"""DataSet — uploaded data source (CSV / XLSX / SQLite) the user maps onto template placeholders."""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

JsonField = JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(UTC)


class DataSetSourceType(enum.StrEnum):
    CSV = "csv"
    XLSX = "xlsx"
    SQLITE = "sqlite"


class DataSet(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_format: Mapped[str] = mapped_column(String(10), nullable=False)
    source_type: Mapped[DataSetSourceType] = mapped_column(
        SAEnum(
            DataSetSourceType,
            name="dataset_source_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=DataSetSourceType.CSV,
    )
    # SQLite-only: the table OR the SELECT to read at render time.
    # At most one is set (DB-level CHECK); both NULL means "uploaded but not yet configured".
    sqlite_table: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sqlite_query: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Snapshot of structure so the wizard can show columns without re-parsing.
    columns: Mapped[list[Any]] = mapped_column(JsonField, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    def __repr__(self) -> str:
        return f"<DataSet id={self.id} {self.original_filename} {self.row_count} rows>"
