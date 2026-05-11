"""User-shaped schemas for responses + admin requests."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Role
from app.schemas.types import LooseEmail


class UserPublic(BaseModel):
    """User shape exposed to API consumers (no password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: Role
    language: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    last_login_at: datetime | None


class CreateUserRequest(BaseModel):
    email: LooseEmail
    role: Role = Role.EDITOR
    language: str = Field(default="pl", min_length=2, max_length=8)
    temporary_password: str = Field(min_length=10, max_length=256)


class UpdateUserRequest(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
    language: str | None = Field(default=None, min_length=2, max_length=8)


class ResetPasswordRequest(BaseModel):
    new_temporary_password: str = Field(min_length=10, max_length=256)


class CreateUserResponse(BaseModel):
    user: UserPublic
    temporary_password: str  # echoed back so admin can pass it to the user
