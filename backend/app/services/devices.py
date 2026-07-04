"""Device management for the local connector. No Flask coupling."""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.device import TOKEN_PREFIX, hash_token
from app.models.device import Device


class DeviceNameTakenError(ValueError):
    pass


class DeviceNotFoundError(LookupError):
    pass


def create_device(session: Session, *, owner_id: int, name: str) -> tuple[Device, str]:
    """Create a device and return it with the plaintext token.

    The token is shown to the user exactly once — only its hash persists."""
    token = TOKEN_PREFIX + secrets.token_hex(32)
    device = Device(owner_id=owner_id, name=name, token_hash=hash_token(token))
    session.add(device)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DeviceNameTakenError(name) from exc
    session.refresh(device)
    return device, token


def list_devices(session: Session, *, owner_id: int) -> list[Device]:
    stmt = select(Device).where(Device.owner_id == owner_id).order_by(Device.created_at)
    return list(session.scalars(stmt))


def get_owned_device(session: Session, device_id: int, *, owner_id: int, is_admin: bool) -> Device:
    device = session.get(Device, device_id)
    if device is None or (device.owner_id != owner_id and not is_admin):
        raise DeviceNotFoundError(device_id)
    return device


def delete_device(session: Session, device_id: int, *, owner_id: int, is_admin: bool) -> None:
    device = get_owned_device(session, device_id, owner_id=owner_id, is_admin=is_admin)
    session.delete(device)
    session.commit()
