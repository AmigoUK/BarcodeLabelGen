"""Template CRUD service — owner-scoped queries, optimistic version bump."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.label_format import LabelFormat
from app.models.template import Template


class TemplateNotFoundError(LookupError):
    pass


class TemplateAccessError(PermissionError):
    """Returned when a non-owner asks to mutate a template they don't own."""


def list_mine(
    session: Session, *, owner_id: int, folder_id: int | None = None, unfiled_only: bool = False
) -> list[Template]:
    """The user's own templates, optionally narrowed to one folder or to
    templates outside any folder ("Bez folderu")."""
    stmt = select(Template).where(Template.owner_id == owner_id)
    if unfiled_only:
        stmt = stmt.where(Template.folder_id.is_(None))
    elif folder_id is not None:
        stmt = stmt.where(Template.folder_id == folder_id)
    return list(session.execute(stmt.order_by(Template.updated_at.desc())).scalars().all())


def list_library(session: Session) -> list[Template]:
    """Everything shared into the library, regardless of owner."""
    stmt = (
        select(Template)
        .where(Template.is_shared.is_(True))
        .order_by(Template.updated_at.desc())
    )
    return list(session.execute(stmt).scalars().all())


def clone(session: Session, template_id: int, *, requesting_user_id: int) -> Template:
    """\"Użyj\": copy an accessible template (own or shared) into the caller's
    templates. Assets are owner-scoped, so image objects get their binaries
    copied into the caller's library (deduped by sha256 against what the
    caller already has)."""
    from copy import deepcopy

    from app.services import assets as assets_svc

    src = get(session, template_id, requesting_user_id=requesting_user_id)
    canvas = deepcopy(src.canvas_data)

    if src.owner_id != requesting_user_id:
        remap: dict[int, int] = {}
        for obj in canvas.get("objects", []) or []:
            if obj.get("type") != "image":
                continue
            asset_id = obj.get("assetId")
            if not isinstance(asset_id, int):
                continue
            if asset_id not in remap:
                src_asset = assets_svc.get_asset(session, asset_id)
                if src_asset is None:
                    continue
                existing = (
                    assets_svc.find_by_sha256(
                        session, owner_id=requesting_user_id, sha256=src_asset.sha256
                    )
                    if src_asset.sha256
                    else None
                )
                if existing is not None:
                    remap[asset_id] = existing.id
                else:
                    raw = (assets_svc.assets_dir() / src_asset.storage_filename).read_bytes()
                    copied = assets_svc.save_image_from_bytes(
                        session,
                        owner_id=requesting_user_id,
                        original_filename=src_asset.original_filename,
                        raw=raw,
                        declared_mime=src_asset.mime_type,
                    )
                    remap[asset_id] = copied.id
            obj["assetId"] = remap[asset_id]

    tpl = Template(
        owner_id=requesting_user_id,
        name=f"{src.name} (kopia)"[:200],
        description=src.description,
        format_id=src.format_id,
        width_mm=src.width_mm,
        height_mm=src.height_mm,
        canvas_data=canvas,
    )
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl


def get(session: Session, template_id: int, *, requesting_user_id: int) -> Template:
    tpl = session.get(Template, template_id)
    if tpl is None:
        raise TemplateNotFoundError(template_id)
    if tpl.owner_id != requesting_user_id and not tpl.is_shared:
        raise TemplateAccessError(template_id)
    return tpl


def create(
    session: Session,
    *,
    owner_id: int,
    name: str,
    description: str | None,
    format_id: int,
    canvas_data: dict[str, Any],
    width_mm: float | None = None,
    height_mm: float | None = None,
) -> Template:
    """Create a Template snapshotting either the format's dimensions or the
    optional `width_mm` / `height_mm` overrides (used for landscape
    orientation and the Custom-size flow). Each override falls back
    independently to the format value if the client only sent one — the UI
    always sends both or neither, but staying defensive avoids surprises."""
    label_format = session.get(LabelFormat, format_id)
    if label_format is None:
        raise ValueError(f"label_format {format_id} not found")

    final_w = float(width_mm) if width_mm is not None else float(label_format.width_mm)
    final_h = float(height_mm) if height_mm is not None else float(label_format.height_mm)

    tpl = Template(
        owner_id=owner_id,
        name=name,
        description=description,
        format_id=format_id,
        width_mm=final_w,
        height_mm=final_h,
        canvas_data=canvas_data or _empty_canvas(final_w, final_h),
    )
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl


def update(
    session: Session,
    template_id: int,
    *,
    requesting_user_id: int,
    name: str | None = None,
    description: str | None = None,
    canvas_data: dict[str, Any] | None = None,
    is_shared: bool | None = None,
    width_mm: float | None = None,
    height_mm: float | None = None,
    folder_id: int | None = None,
    folder_id_set: bool = False,
) -> Template:
    tpl = session.get(Template, template_id)
    if tpl is None:
        raise TemplateNotFoundError(template_id)
    if tpl.owner_id != requesting_user_id:
        raise TemplateAccessError(template_id)

    if folder_id_set:
        if folder_id is not None:
            # Folder must exist and belong to the same user.
            from app.services.folders import get_owned_folder

            get_owned_folder(session, folder_id, owner_id=requesting_user_id)
        tpl.folder_id = folder_id

    if name is not None:
        tpl.name = name
    if description is not None:
        tpl.description = description
    if is_shared is not None:
        tpl.is_shared = is_shared
    if width_mm is not None:
        tpl.width_mm = float(width_mm)
    if height_mm is not None:
        tpl.height_mm = float(height_mm)
    if canvas_data is not None:
        tpl.canvas_data = canvas_data
        tpl.version += 1

    session.commit()
    session.refresh(tpl)
    return tpl


def delete(session: Session, template_id: int, *, requesting_user_id: int) -> None:
    tpl = session.get(Template, template_id)
    if tpl is None:
        raise TemplateNotFoundError(template_id)
    if tpl.owner_id != requesting_user_id:
        raise TemplateAccessError(template_id)
    session.delete(tpl)
    session.commit()


def _empty_canvas(width_mm: float, height_mm: float) -> dict[str, Any]:
    """Initial Konva-stage shape for a brand-new template."""
    return {
        "version": 1,
        "stage": {
            "width_mm": float(width_mm),
            "height_mm": float(height_mm),
        },
        "objects": [],
    }
