"""Captures inbox (connector phase D)

Revision ID: 0008_captures
Revises: 0007_devices_print_jobs
Create Date: 2026-07-04 10:00:00

ZPL print jobs intercepted by the agent's virtual-printer listener,
uploaded per device and reviewed in the web app's Inbox.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_captures"
down_revision: str | None = "0007_devices_print_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "captures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("zpl", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name=op.f("fk_captures_device_id_devices"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_captures")),
    )
    op.create_index(op.f("ix_captures_device_id"), "captures", ["device_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_captures_device_id"), table_name="captures")
    op.drop_table("captures")
