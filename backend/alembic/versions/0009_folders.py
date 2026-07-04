"""Template folders (F31)

Revision ID: 0009_folders
Revises: 0008_captures
Create Date: 2026-07-04 12:00:00

Flat, per-user template folders. templates.folder_id is SET NULL on
folder delete — removing a folder never removes its templates.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_folders"
down_revision: str | None = "0008_captures"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "folders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_folders_owner_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_folders")),
        sa.UniqueConstraint("owner_id", "name", name=op.f("uq_folders_owner_id")),
    )
    op.create_index(op.f("ix_folders_owner_id"), "folders", ["owner_id"], unique=False)

    op.add_column("templates", sa.Column("folder_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_templates_folder_id"), "templates", ["folder_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_templates_folder_id_folders"),
        "templates",
        "folders",
        ["folder_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_templates_folder_id_folders"), "templates", type_="foreignkey")
    op.drop_index(op.f("ix_templates_folder_id"), table_name="templates")
    op.drop_column("templates", "folder_id")
    op.drop_index(op.f("ix_folders_owner_id"), table_name="folders")
    op.drop_table("folders")
