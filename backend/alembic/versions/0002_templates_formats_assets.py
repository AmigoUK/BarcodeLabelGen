"""Templates, label formats, assets

Revision ID: 0002_templates_formats_assets
Revises: 0001_initial_users
Create Date: 2026-05-11 11:42:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_templates_formats_assets"
down_revision: str | None = "0001_initial_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "label_formats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("width_mm", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("height_mm", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("a_paper", "zebra", "custom", name="format_kind"),
            nullable=False,
        ),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_label_formats")),
    )

    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("format_id", sa.Integer(), nullable=False),
        sa.Column("width_mm", sa.Float(), nullable=False),
        sa.Column("height_mm", sa.Float(), nullable=False),
        sa.Column("canvas_data", JSONB(), nullable=False),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_templates_owner_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["format_id"],
            ["label_formats.id"],
            ondelete="RESTRICT",
            name=op.f("fk_templates_format_id_label_formats"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_templates")),
    )
    op.create_index(op.f("ix_templates_owner_id"), "templates", ["owner_id"], unique=False)

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("storage_filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width_px", sa.Integer(), nullable=False),
        sa.Column("height_px", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_assets_owner_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assets")),
    )
    op.create_index(op.f("ix_assets_owner_id"), "assets", ["owner_id"], unique=False)

    # Seed system label formats — A4-family + common Zebra rolls.
    # `kind` declared as Enum here so Postgres applies the proper enum cast
    # instead of a varchar→enum mismatch.
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
                "name": "A4 (210×297 mm)",
                "width_mm": 210,
                "height_mm": 297,
                "kind": "a_paper",
                "is_system": True,
            },
            {
                "name": "A5 (148×210 mm)",
                "width_mm": 148,
                "height_mm": 210,
                "kind": "a_paper",
                "is_system": True,
            },
            {
                "name": "A6 (105×148 mm)",
                "width_mm": 105,
                "height_mm": 148,
                "kind": "a_paper",
                "is_system": True,
            },
            {
                "name": 'Zebra 4×6"',
                "width_mm": 101.6,
                "height_mm": 152.4,
                "kind": "zebra",
                "is_system": True,
            },
            {
                "name": 'Zebra 4×4"',
                "width_mm": 101.6,
                "height_mm": 101.6,
                "kind": "zebra",
                "is_system": True,
            },
            {
                "name": 'Zebra 3×2"',
                "width_mm": 76.2,
                "height_mm": 50.8,
                "kind": "zebra",
                "is_system": True,
            },
            {
                "name": 'Zebra 2×1"',
                "width_mm": 50.8,
                "height_mm": 25.4,
                "kind": "zebra",
                "is_system": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_assets_owner_id"), table_name="assets")
    op.drop_table("assets")
    op.drop_index(op.f("ix_templates_owner_id"), table_name="templates")
    op.drop_table("templates")
    op.drop_table("label_formats")
    sa.Enum(name="format_kind").drop(op.get_bind(), checkfirst=True)
