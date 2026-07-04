"""Template version history — snapshots on manual save. No Flask coupling."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.template import Template
from app.models.template_version import TemplateVersion

# Keep the last N snapshots per template; older ones drop on the next save.
MAX_VERSIONS_PER_TEMPLATE = 30


class VersionNotFoundError(LookupError):
    pass


def snapshot(
    session: Session, tpl: Template, *, created_by: int, note: str | None = None
) -> TemplateVersion:
    """Record the template's current canvas as version `tpl.version`, then
    trim to the retention cap. Caller bumps tpl.version before/after per its
    own flow; here we just persist the row at the template's current number."""
    row = TemplateVersion(
        template_id=tpl.id,
        version=tpl.version,
        canvas_data=tpl.canvas_data,
        width_mm=tpl.width_mm,
        height_mm=tpl.height_mm,
        note=note,
        created_by=created_by,
    )
    session.add(row)
    session.flush()

    stale = list(
        session.scalars(
            select(TemplateVersion.id)
            .where(TemplateVersion.template_id == tpl.id)
            .order_by(TemplateVersion.version.desc())
            .offset(MAX_VERSIONS_PER_TEMPLATE)
        )
    )
    if stale:
        for old in session.scalars(
            select(TemplateVersion).where(TemplateVersion.id.in_(stale))
        ):
            session.delete(old)
    return row


def list_versions(session: Session, template_id: int) -> list[TemplateVersion]:
    stmt = (
        select(TemplateVersion)
        .where(TemplateVersion.template_id == template_id)
        .order_by(TemplateVersion.version.desc())
    )
    return list(session.scalars(stmt))


def get_version(session: Session, template_id: int, version: int) -> TemplateVersion:
    row = session.scalar(
        select(TemplateVersion).where(
            TemplateVersion.template_id == template_id, TemplateVersion.version == version
        )
    )
    if row is None:
        raise VersionNotFoundError(version)
    return row
