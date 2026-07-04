"""Generated-file history (F18)

Revision ID: 0012_generated_files
Revises: 0011_template_versions
Create Date: 2026-07-04 18:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012_generated_files"
down_revision: str | None = "0011_template_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generated_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("template_name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("mode", sa.String(length=8), nullable=False),
        sa.Column("storage_filename", sa.String(length=255), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_generated_files_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name=op.f("fk_generated_files_template_id_templates"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generated_files")),
    )
    op.create_index(
        op.f("ix_generated_files_owner_id"), "generated_files", ["owner_id"], unique=False
    )
    op.create_index(
        op.f("ix_generated_files_created_at"), "generated_files", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_generated_files_created_at"), table_name="generated_files")
    op.drop_index(op.f("ix_generated_files_owner_id"), table_name="generated_files")
    op.drop_table("generated_files")
