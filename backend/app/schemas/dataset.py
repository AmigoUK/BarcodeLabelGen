"""Request/response schemas for /api/datasets/*."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.services.datasets import FilterOp


class DataSetPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    file_format: str
    columns: list[str]
    row_count: int
    size_bytes: int
    uploaded_at: datetime


class FilterRequest(BaseModel):
    column: str = Field(min_length=1, max_length=255)
    op: FilterOp
    value: str = Field(default="", max_length=1000)


class FilterResponse(BaseModel):
    match_count: int
    preview: list[dict[str, str]]
