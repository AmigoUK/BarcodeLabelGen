from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.user import Role
from app.services.users import (
    EmailAlreadyExistsError,
    UserNotFoundError,
    authenticate,
    change_own_password,
    create_user,
    get_user_by_email,
    list_users,
    reset_password,
    update_user,
)


def test_create_user_persists_with_hashed_password(db_session: Session) -> None:
    user = create_user(db_session, email="alice@example.com", plain_password="password123")
    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.password_hash.startswith("$argon2id$")
    assert user.role is Role.EDITOR
    assert user.must_change_password is True


def test_create_user_lowercases_email(db_session: Session) -> None:
    user = create_user(db_session, email="MIXED@Example.COM", plain_password="password123")
    assert user.email == "mixed@example.com"


def test_create_user_duplicate_email_raises(db_session: Session) -> None:
    create_user(db_session, email="dup@example.com", plain_password="password123")
    with pytest.raises(EmailAlreadyExistsError):
        create_user(db_session, email="dup@example.com", plain_password="otherPassword456")


def test_get_user_by_email_case_insensitive(db_session: Session) -> None:
    create_user(db_session, email="case@example.com", plain_password="password123")
    found = get_user_by_email(db_session, "CASE@example.com")
    assert found is not None
    assert found.email == "case@example.com"


def test_authenticate_succeeds_for_valid_credentials(db_session: Session) -> None:
    create_user(db_session, email="bob@example.com", plain_password="bobsPassword123")
    result = authenticate(db_session, "bob@example.com", "bobsPassword123")
    assert result is not None
    assert result.email == "bob@example.com"
    assert result.last_login_at is not None


def test_authenticate_fails_for_wrong_password(db_session: Session) -> None:
    create_user(db_session, email="bob@example.com", plain_password="bobsPassword123")
    assert authenticate(db_session, "bob@example.com", "wrongPassword") is None


def test_authenticate_fails_for_unknown_user(db_session: Session) -> None:
    assert authenticate(db_session, "nobody@example.com", "anything") is None


def test_authenticate_fails_for_disabled_user(db_session: Session) -> None:
    user = create_user(db_session, email="disabled@example.com", plain_password="password123")
    update_user(db_session, user.id, is_active=False)
    assert authenticate(db_session, "disabled@example.com", "password123") is None


def test_change_own_password_clears_must_change_flag(db_session: Session) -> None:
    user = create_user(db_session, email="cp@example.com", plain_password="oldPassword123")
    assert user.must_change_password is True

    ok = change_own_password(
        db_session, user, current_plain="oldPassword123", new_plain="newPassword456"
    )
    assert ok is True
    db_session.refresh(user)
    assert user.must_change_password is False
    assert authenticate(db_session, "cp@example.com", "newPassword456") is not None
    assert authenticate(db_session, "cp@example.com", "oldPassword123") is None


def test_change_own_password_rejects_wrong_current_password(db_session: Session) -> None:
    user = create_user(db_session, email="cp@example.com", plain_password="oldPassword123")
    ok = change_own_password(db_session, user, current_plain="wrong", new_plain="newPassword456")
    assert ok is False


def test_admin_reset_password_re_enables_must_change_flag(db_session: Session) -> None:
    user = create_user(db_session, email="r@example.com", plain_password="oldPassword123")
    change_own_password(
        db_session, user, current_plain="oldPassword123", new_plain="newPassword456"
    )
    assert user.must_change_password is False

    reset = reset_password(db_session, user.id, "tempReset789")
    assert reset.must_change_password is True
    assert authenticate(db_session, "r@example.com", "tempReset789") is not None


def test_update_user_can_change_role(db_session: Session) -> None:
    user = create_user(db_session, email="u@example.com", plain_password="password123")
    updated = update_user(db_session, user.id, role=Role.ADMIN)
    assert updated.role is Role.ADMIN


def test_update_user_unknown_id_raises(db_session: Session) -> None:
    with pytest.raises(UserNotFoundError):
        update_user(db_session, 999_999, role=Role.ADMIN)


def test_list_users_returns_newest_first(db_session: Session) -> None:
    create_user(db_session, email="first@example.com", plain_password="password123")
    create_user(db_session, email="second@example.com", plain_password="password123")
    users = list_users(db_session)
    assert [u.email for u in users] == ["second@example.com", "first@example.com"]
