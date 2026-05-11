"""Password hashing using Argon2id (memory-hard, side-channel resistant)."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Parameters from PROJECT.md §9.1: memory=64 MiB, iterations=3, parallelism=4
_hasher = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=4)


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(hashed: str, plain: str) -> bool:
    try:
        _hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    return True


def needs_rehash(hashed: str) -> bool:
    return _hasher.check_needs_rehash(hashed)


# Pre-computed dummy hash used for constant-time defense when authenticating
# unknown users — verifying against this keeps the per-request CPU cost roughly
# the same whether the email exists or not, frustrating user-enumeration timing.
DUMMY_HASH = _hasher.hash("constant-time-defense-dummy-value")
