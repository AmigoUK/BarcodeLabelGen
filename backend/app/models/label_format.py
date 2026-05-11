"""Label format — predefined paper/sticker sizes plus user-defined custom sizes."""

from __future__ import annotations

import enum

from sqlalchemy import Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FormatKind(enum.StrEnum):
    A_PAPER = "a_paper"  # A4, A5, A6
    ZEBRA = "zebra"  # standard label-printer rolls
    CUSTOM = "custom"


class LabelFormat(Base):
    """Either a system preset (owner_id NULL) or a user-defined custom size."""

    __tablename__ = "label_formats"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    width_mm: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)
    height_mm: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)
    kind: Mapped[FormatKind] = mapped_column(
        Enum(
            FormatKind,
            name="format_kind",
            values_callable=lambda e: [k.value for k in e],
        ),
        nullable=False,
    )
    is_system: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<LabelFormat {self.name} {self.width_mm}×{self.height_mm}mm>"
