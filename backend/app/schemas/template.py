"""Schemas for template + label-format + asset endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LabelFormatPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    width_mm: float
    height_mm: float
    kind: str
    is_system: bool


class TemplateSummary(BaseModel):
    """Light shape for catalog listings — no canvas_data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    owner_id: int
    format_id: int
    width_mm: float
    height_mm: float
    is_shared: bool
    version: int
    created_at: datetime
    updated_at: datetime


class TemplatePublic(TemplateSummary):
    """Full shape including canvas_data — used when opening in editor."""

    canvas_data: dict[str, Any]


class CreateTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    format_id: int
    canvas_data: dict[str, Any] = Field(default_factory=dict)


class UpdateTemplateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    canvas_data: dict[str, Any] | None = None
    is_shared: bool | None = None


class AssetPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    mime_type: str
    size_bytes: int
    width_px: int
    height_px: int
    created_at: datetime
