"""Folder colors + template featured image (F32/F33)

Revision ID: 0010_folder_color_featured_image
Revises: 0009_folders
Create Date: 2026-07-04 14:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_folder_color_featured_image"
down_revision: str | None = "0009_folders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("folders", sa.Column("color", sa.String(length=7), nullable=True))
    op.add_column("templates", sa.Column("featured_asset_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_templates_featured_asset_id_assets"),
        "templates",
        "assets",
        ["featured_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_templates_featured_asset_id_assets"), "templates", type_="foreignkey"
    )
    op.drop_column("templates", "featured_asset_id")
    op.drop_column("folders", "color")
