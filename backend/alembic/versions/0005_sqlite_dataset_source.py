"""SQLite dataset source

Revision ID: 0005_sqlite_dataset_source
Revises: 0004_custom_label_format
Create Date: 2026-05-12 18:00:00

Adds a `source_type` discriminator to datasets so a Dataset can come
from a SQLite file (in addition to CSV/XLSX). For SQLite-backed
datasets we also store either `sqlite_table` (table-picker mode) or
`sqlite_query` (custom SELECT mode) — DB-level CHECK ensures the two
are mutually exclusive (both NULL until the user finalizes the choice).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_sqlite_dataset_source"
down_revision: str | None = "0004_custom_label_format"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SOURCE_TYPE_VALUES = ("csv", "xlsx", "sqlite")


def upgrade() -> None:
    source_type_enum = sa.Enum(*SOURCE_TYPE_VALUES, name="dataset_source_type")
    source_type_enum.create(op.get_bind(), checkfirst=True)

    # Step 1: add source_type with a server-side default of 'csv' so existing
    # rows pick up a sane value, then backfill from file_format below.
    op.add_column(
        "datasets",
        sa.Column(
            "source_type",
            sa.Enum(*SOURCE_TYPE_VALUES, name="dataset_source_type", create_type=False),
            nullable=False,
            server_default="csv",
        ),
    )
    op.add_column("datasets", sa.Column("sqlite_table", sa.String(length=128), nullable=True))
    op.add_column("datasets", sa.Column("sqlite_query", sa.Text(), nullable=True))

    # Backfill: existing rows have file_format ∈ {'csv','xlsx'} → mirror it.
    op.execute(
        "UPDATE datasets SET source_type = file_format::dataset_source_type "
        "WHERE file_format IN ('csv', 'xlsx')"
    )

    # At-most-one invariant on the two SQLite-config columns. Both NULL is fine
    # (uploaded-but-not-configured); both set is rejected. Application layer
    # additionally enforces "exactly one" once the user finalizes config.
    op.create_check_constraint(
        "ck_datasets_sqlite_table_xor_query",
        "datasets",
        "(sqlite_table IS NULL) OR (sqlite_query IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_datasets_sqlite_table_xor_query", "datasets", type_="check")
    op.drop_column("datasets", "sqlite_query")
    op.drop_column("datasets", "sqlite_table")
    op.drop_column("datasets", "source_type")
    sa.Enum(name="dataset_source_type").drop(op.get_bind(), checkfirst=True)
