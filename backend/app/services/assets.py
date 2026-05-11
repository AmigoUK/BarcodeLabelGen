"""Image asset upload + retrieval — files live on disk, metadata in DB."""

from __future__ import annotations

import io
import os
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset

ALLOWED_MIME = {"image/png", "image/jpeg", "image/svg+xml"}
ALLOWED_EXT = {"png", "jpg", "jpeg", "svg"}
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB per PROJECT.md §9.2


class AssetUploadError(ValueError):
    pass


def assets_dir() -> Path:
    """Where uploaded images live; container path matches the docker volume."""
    return Path(os.environ.get("ASSETS_DIR", "/app/assets"))


def save_image(
    session: Session,
    *,
    owner_id: int,
    original_filename: str,
    raw: bytes,
    declared_mime: str,
) -> Asset:
    if len(raw) > MAX_SIZE_BYTES:
        raise AssetUploadError(f"file exceeds {MAX_SIZE_BYTES} bytes limit")
    if declared_mime not in ALLOWED_MIME:
        raise AssetUploadError(f"mime type {declared_mime} not allowed")

    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
    if ext not in ALLOWED_EXT:
        raise AssetUploadError(f"extension .{ext} not allowed")

    width = height = 0
    if declared_mime != "image/svg+xml":
        try:
            with Image.open(io.BytesIO(raw)) as img:
                width, height = img.size
                # Re-encode to strip metadata + verify it's a real image.
                buf = io.BytesIO()
                fmt = "PNG" if declared_mime == "image/png" else "JPEG"
                img.convert("RGBA" if fmt == "PNG" else "RGB").save(buf, format=fmt)
                raw = buf.getvalue()
        except UnidentifiedImageError as exc:
            raise AssetUploadError("file is not a valid image") from exc

    storage_filename = f"{uuid.uuid4().hex}.{ext}"
    target = assets_dir() / storage_filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)

    asset = Asset(
        owner_id=owner_id,
        storage_filename=storage_filename,
        original_filename=original_filename,
        mime_type=declared_mime,
        size_bytes=len(raw),
        width_px=width,
        height_px=height,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def get_asset(session: Session, asset_id: int) -> Asset | None:
    return session.get(Asset, asset_id)


def list_user_assets(session: Session, *, owner_id: int) -> list[Asset]:
    stmt = select(Asset).where(Asset.owner_id == owner_id).order_by(Asset.created_at.desc())
    return list(session.execute(stmt).scalars().all())
