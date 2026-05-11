from __future__ import annotations

from app.auth.password import hash_password, verify_password


def test_hash_password_returns_argon2id_string() -> None:
    h = hash_password("super-secret-password")
    assert h.startswith("$argon2id$")


def test_verify_password_accepts_correct_password() -> None:
    h = hash_password("super-secret-password")
    assert verify_password(h, "super-secret-password") is True


def test_verify_password_rejects_wrong_password() -> None:
    h = hash_password("super-secret-password")
    assert verify_password(h, "wrong-password") is False


def test_each_hash_uses_unique_salt() -> None:
    h1 = hash_password("same-password")
    h2 = hash_password("same-password")
    assert h1 != h2
