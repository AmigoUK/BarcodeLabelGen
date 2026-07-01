"""Template CRUD service — owner-scoped queries, optimistic version bump."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.label_format import LabelFormat
from app.models.template import Template


class TemplateNotFoundError(LookupError):
    pass


class TemplateAccessError(PermissionError):
    """Returned when a non-owner asks to mutate a template they don't own."""


def list_visible(session: Session, *, owner_id: int) -> list[Template]:
    """All templates the user can see: owned + globally shared."""
    stmt = (
        select(Template)
        .where(or_(Template.owner_id == owner_id, Template.is_shared.is_(True)))
        .order_by(Template.updated_at.desc())
    )
    return list(session.execute(stmt).scalars().all())


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
) -> Template:
    tpl = session.get(Template, template_id)
    if tpl is None:
        raise TemplateNotFoundError(template_id)
    if tpl.owner_id != requesting_user_id:
        raise TemplateAccessError(template_id)

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
