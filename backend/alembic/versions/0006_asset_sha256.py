"""Asset SHA-256

Revision ID: 0006_asset_sha256
Revises: 0005_sqlite_dataset_source
Create Date: 2026-05-13 14:00:00

Adds a `sha256` column on assets so the template-import flow can detect
that an incoming image is identical (byte-for-byte) to one the user
already has, and offer to reuse the existing row instead of creating
a duplicate. The column is nullable; backfill reads each on-disk file
and computes the hash. Re-runs are idempotent — rows that already have
a value are left alone.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_asset_sha256"
down_revision: str | None = "0005_sqlite_dataset_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.create_index(
        "ix_assets_owner_sha256",
        "assets",
        ["owner_id", "sha256"],
        unique=False,
    )

    # Backfill from disk. Missing files are left with sha256 = NULL — the
    # service code tolerates that and recomputes on demand. Idempotent: only
    # rows where sha256 IS NULL get touched.
    assets_dir = Path(os.environ.get("ASSETS_DIR", "/app/assets"))
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, storage_filename FROM assets WHERE sha256 IS NULL")
    ).fetchall()
    for row in rows:
        path = assets_dir / row.storage_filename
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        bind.execute(
            sa.text("UPDATE assets SET sha256 = :h WHERE id = :i"),
            {"h": digest, "i": row.id},
        )


def downgrade() -> None:
    op.drop_index("ix_assets_owner_sha256", table_name="assets")
    op.drop_column("assets", "sha256")
