"""Devices + print jobs (connector phase B)

Revision ID: 0007_devices_print_jobs
Revises: 0006_asset_sha256
Create Date: 2026-07-04 09:00:00

Adds the server side of the local connector: `devices` (per-device Bearer
tokens, stored as SHA-256 digests, plus agent-reported printer list) and
`print_jobs` (queued ZPL jobs polled by the agent).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_devices_print_jobs"
down_revision: str | None = "0006_asset_sha256"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("agent_version", sa.String(length=50), nullable=True),
        sa.Column("printers", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_devices_owner_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_devices")),
        sa.UniqueConstraint("owner_id", "name", name=op.f("uq_devices_owner_id")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_devices_token_hash")),
    )
    op.create_index(op.f("ix_devices_owner_id"), "devices", ["owner_id"], unique=False)

    op.create_table(
        "print_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("printer", sa.String(length=100), nullable=False),
        sa.Column("copies", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("zpl", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "sent", "done", "error", name="print_job_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name=op.f("fk_print_jobs_device_id_devices"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_print_jobs_created_by_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_print_jobs")),
    )
    op.create_index(op.f("ix_print_jobs_device_id"), "print_jobs", ["device_id"], unique=False)
    op.create_index(op.f("ix_print_jobs_created_by"), "print_jobs", ["created_by"], unique=False)
    op.create_index(op.f("ix_print_jobs_status"), "print_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_print_jobs_status"), table_name="print_jobs")
    op.drop_index(op.f("ix_print_jobs_created_by"), table_name="print_jobs")
    op.drop_index(op.f("ix_print_jobs_device_id"), table_name="print_jobs")
    op.drop_table("print_jobs")
    op.drop_index(op.f("ix_devices_owner_id"), table_name="devices")
    op.drop_table("devices")
    sa.Enum(name="print_job_status").drop(op.get_bind(), checkfirst=True)
