"""Flat, per-user template folders. No Flask coupling."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.folder import Folder
from app.models.template import Template


class FolderNameTakenError(ValueError):
    pass


class FolderNotFoundError(LookupError):
    pass


def list_folders(session: Session, *, owner_id: int) -> list[tuple[Folder, int]]:
    """Folders with their template counts, alphabetically."""
    stmt = (
        select(Folder, func.count(Template.id))
        .outerjoin(Template, Template.folder_id == Folder.id)
        .where(Folder.owner_id == owner_id)
        .group_by(Folder.id)
        .order_by(Folder.name)
    )
    return [(folder, count) for folder, count in session.execute(stmt).all()]


def get_owned_folder(session: Session, folder_id: int, *, owner_id: int) -> Folder:
    folder = session.get(Folder, folder_id)
    if folder is None or folder.owner_id != owner_id:
        raise FolderNotFoundError(folder_id)
    return folder


def create_folder(session: Session, *, owner_id: int, name: str, color: str | None = None) -> Folder:
    folder = Folder(owner_id=owner_id, name=name, color=color)
    session.add(folder)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise FolderNameTakenError(name) from exc
    session.refresh(folder)
    return folder


def update_folder(
    session: Session,
    folder_id: int,
    *,
    owner_id: int,
    name: str | None = None,
    color: str | None = None,
    color_set: bool = False,
) -> Folder:
    folder = get_owned_folder(session, folder_id, owner_id=owner_id)
    if name is not None:
        folder.name = name
    if color_set:
        folder.color = color
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise FolderNameTakenError(name or folder.name) from exc
    session.refresh(folder)
    return folder


def delete_folder(session: Session, folder_id: int, *, owner_id: int) -> None:
    """Delete a folder; its templates fall back to "no folder" (FK SET NULL
    covers Postgres; the explicit UPDATE keeps SQLite tests honest too)."""
    folder = get_owned_folder(session, folder_id, owner_id=owner_id)
    for tpl in session.scalars(select(Template).where(Template.folder_id == folder.id)):
        tpl.folder_id = None
    session.delete(folder)
    session.commit()
