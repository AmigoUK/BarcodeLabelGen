"""Captured-ZPL inbox for the connector's virtual printer. No Flask coupling."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.capture import Capture
from app.models.device import Device

# Oldest captures beyond this per-device count are dropped on insert —
# the inbox is a review queue, not an archive.
MAX_CAPTURES_PER_DEVICE = 200


class CaptureNotFoundError(LookupError):
    pass


def add_capture(session: Session, *, device_id: int, zpl: str) -> Capture:
    capture = Capture(device_id=device_id, zpl=zpl, size_bytes=len(zpl.encode("utf-8")))
    session.add(capture)
    session.flush()

    stale = list(
        session.scalars(
            select(Capture.id)
            .where(Capture.device_id == device_id)
            .order_by(Capture.created_at.desc(), Capture.id.desc())
            .offset(MAX_CAPTURES_PER_DEVICE)
        )
    )
    if stale:
        for cap in session.scalars(select(Capture).where(Capture.id.in_(stale))):
            session.delete(cap)
    session.commit()
    session.refresh(capture)
    return capture


def list_captures_for_user(session: Session, *, user_id: int, limit: int = 100) -> list[Capture]:
    stmt = (
        select(Capture)
        .join(Device, Capture.device_id == Device.id)
        .where(Device.owner_id == user_id)
        .order_by(Capture.created_at.desc(), Capture.id.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def get_capture_for_user(session: Session, capture_id: int, *, user_id: int) -> Capture:
    capture = session.get(Capture, capture_id)
    if capture is None:
        raise CaptureNotFoundError(capture_id)
    device = session.get(Device, capture.device_id)
    if device is None or device.owner_id != user_id:
        raise CaptureNotFoundError(capture_id)
    return capture


def delete_capture(session: Session, capture_id: int, *, user_id: int) -> None:
    capture = get_capture_for_user(session, capture_id, user_id=user_id)
    session.delete(capture)
    session.commit()
