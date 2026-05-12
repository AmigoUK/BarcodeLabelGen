"""Request/response schemas for /api/datasets/*."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.dataset import DataSetSourceType
from app.services.datasets import FilterOp


class SqliteTableInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    columns: list[str]
    row_count: int


class DataSetPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    file_format: str
    source_type: DataSetSourceType
    columns: list[str]
    row_count: int
    size_bytes: int
    uploaded_at: datetime

    # SQLite-only fields. None for CSV/XLSX, and also None on a freshly
    # uploaded SQLite file before the user picks a table or writes a SELECT.
    sqlite_table: str | None = None
    sqlite_query: str | None = None
    # Transient — populated only by the POST /datasets response for SQLite
    # uploads, so the wizard can render the table picker without a follow-up
    # round-trip. Never persisted, never returned by GET endpoints.
    sqlite_tables: list[SqliteTableInfo] | None = None


class FilterRequest(BaseModel):
    column: str = Field(min_length=1, max_length=255)
    op: FilterOp
    value: str = Field(default="", max_length=1000)


class FilterResponse(BaseModel):
    match_count: int
    preview: list[dict[str, str]]


class SqliteConfigRequest(BaseModel):
    """PATCH /datasets/<id>/sqlite-config body.

    Exactly one of `table` / `query` must be set. Validated server-side
    in addition to the DB CHECK constraint so we surface a clean 400.
    """

    table: str | None = Field(default=None, max_length=128)
    query: str | None = Field(default=None, max_length=4096)

    @model_validator(mode="after")
    def _exactly_one(self) -> SqliteConfigRequest:
        has_table = self.table is not None and self.table.strip() != ""
        has_query = self.query is not None and self.query.strip() != ""
        if has_table == has_query:  # both set OR both empty
            raise ValueError("specify exactly one of 'table' or 'query'")
        return self
