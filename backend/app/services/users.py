"""User CRUD + auth-related queries (no Flask coupling)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.password import DUMMY_HASH, hash_password, needs_rehash, verify_password
from app.models.user import Role, User


class EmailAlreadyExistsError(ValueError):
    """Raised when attempting to create a user with a duplicate email."""


class UserNotFoundError(LookupError):
    """Raised when a user lookup yields no result."""


def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def get_user_by_email(session: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email.lower())
    return session.execute(stmt).scalar_one_or_none()


def list_users(session: Session) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    return list(session.execute(stmt).scalars().all())


def create_user(
    session: Session,
    *,
    email: str,
    plain_password: str,
    role: Role = Role.EDITOR,
    language: str = "pl",
    must_change_password: bool = True,
) -> User:
    user = User(
        email=email.lower(),
        password_hash=hash_password(plain_password),
        role=role,
        language=language,
        must_change_password=must_change_password,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise EmailAlreadyExistsError(email) from exc
    session.refresh(user)
    return user


def update_user(
    session: Session,
    user_id: int,
    *,
    role: Role | None = None,
    is_active: bool | None = None,
    language: str | None = None,
) -> User:
    user = get_user_by_id(session, user_id)
    if user is None:
        raise UserNotFoundError(user_id)
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    if language is not None:
        user.language = language
    session.commit()
    session.refresh(user)
    return user


def reset_password(session: Session, user_id: int, new_plain_password: str) -> User:
    """Admin-issued password reset — sets must_change_password back to True."""
    user = get_user_by_id(session, user_id)
    if user is None:
        raise UserNotFoundError(user_id)
    user.password_hash = hash_password(new_plain_password)
    user.must_change_password = True
    session.commit()
    session.refresh(user)
    return user


def change_own_password(
    session: Session,
    user: User,
    *,
    current_plain: str,
    new_plain: str,
) -> bool:
    """User-initiated password change. Returns False if current password is wrong."""
    if not verify_password(user.password_hash, current_plain):
        return False
    user.password_hash = hash_password(new_plain)
    user.must_change_password = False
    session.commit()
    return True


def authenticate(session: Session, email: str, plain_password: str) -> User | None:
    """Verify credentials. Returns user on success, None on failure (constant-time-ish)."""
    user = get_user_by_email(session, email)
    if user is None or not user.is_active:
        # Run a verify against a real-shape dummy hash to keep timing
        # roughly constant whether the user exists or not.
        verify_password(DUMMY_HASH, plain_password)
        return None
    if not verify_password(user.password_hash, plain_password):
        return None
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(plain_password)
    user.last_login_at = datetime.now(UTC)
    session.commit()
    session.refresh(user)
    return user
