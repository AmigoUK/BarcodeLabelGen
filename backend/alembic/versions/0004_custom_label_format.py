"""Seed shared "Custom" LabelFormat row

Revision ID: 0004_custom_label_format
Revises: 0003_datasets
Create Date: 2026-05-12 06:30:00

Adds a single system-level "Custom" entry to label_formats so the
template-creation modal can reference it via format_id when the user
picks "Custom (define size)". The seeded width/height are placeholders
— the client always sends explicit width_mm / height_mm overrides
through the create-template endpoint and they win over the format's
values in services/templates.create().
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_custom_label_format"
down_revision: str | None = "0003_datasets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    seed_kind_enum = sa.Enum("a_paper", "zebra", "custom", name="format_kind", create_type=False)
    op.bulk_insert(
        sa.table(
            "label_formats",
            sa.column("name", sa.String),
            sa.column("width_mm", sa.Numeric),
            sa.column("height_mm", sa.Numeric),
            sa.column("kind", seed_kind_enum),
            sa.column("is_system", sa.Boolean),
        ),
        [
            {
                "name": "Custom (define size)",
                "width_mm": 100,
                "height_mm": 100,
                "kind": "custom",
                "is_system": True,
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM label_formats WHERE name = 'Custom (define size)' AND kind = 'custom'")
