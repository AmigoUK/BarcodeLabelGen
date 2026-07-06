"""Schemas for template + label-format + asset endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Final, Literal

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
    folder_id: int | None = None
    featured_asset_id: int | None = None
    # Filled only in library listings — who shared this template.
    owner_email: str | None = None
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
    # When set, override the format's dimensions on the new Template row —
    # used for orientation swap (landscape) and the user-typed Custom size.
    # Bounds match the editor's max sensible label (1 m).
    width_mm: float | None = Field(default=None, gt=0, le=1000)
    height_mm: float | None = Field(default=None, gt=0, le=1000)


class UpdateTemplateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    canvas_data: dict[str, Any] | None = None
    is_shared: bool | None = None
    # Label dimensions — editable so a user can resize a template (or correct
    # the size after importing ZPL) without recreating it.
    width_mm: float | None = Field(default=None, gt=0, le=1000)
    height_mm: float | None = Field(default=None, gt=0, le=1000)
    # Explicit null moves the template out of its folder; absent = no change
    # (distinguished via model_fields_set in the route).
    folder_id: int | None = None
    # Explicit null removes the featured image; absent = no change.
    featured_asset_id: int | None = None
    # F17: true = manual save → record a history snapshot + bump version;
    # false/absent = autosave → overwrite the live canvas without a version.
    snapshot: bool = False


class AssetPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    mime_type: str
    size_bytes: int
    width_px: int
    height_px: int
    created_at: datetime


# ---------------- Template export / import ----------------

EXPORT_SCHEMA_ID: Final = "blg-template/v1"

ImageMimeType = Literal["image/png", "image/jpeg", "image/svg+xml"]


class AssetExport(BaseModel):
    """One image bundled inside a `.blg-template.json` file."""

    ref: str = Field(min_length=1, max_length=64)
    original_filename: str = Field(min_length=1, max_length=255)
    mime_type: ImageMimeType
    width_px: int = Field(ge=0)  # SVG can legitimately be 0; PIL won't size it
    height_px: int = Field(ge=0)
    size_bytes: int = Field(ge=1, le=5 * 1024 * 1024)
    sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    data_b64: str = Field(min_length=4)


class FormatHint(BaseModel):
    """LabelFormat name + dimensions, embedded informationally so the importer
    can try to bind to an existing format on the target instance."""

    name: str
    width_mm: float = Field(gt=0, le=2000)
    height_mm: float = Field(gt=0, le=2000)


class TemplateExportMeta(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    width_mm: float = Field(gt=0, le=2000)
    height_mm: float = Field(gt=0, le=2000)
    format_hint: FormatHint | None = None


class TemplateExport(BaseModel):
    """The complete on-wire shape of a `.blg-template.json` file."""

    model_config = ConfigDict(populate_by_name=True)

    schema_id: Literal["blg-template/v1"] = Field(alias="$schema")
    exportedAt: datetime
    exportedBy: str | None = None
    exporter: dict[str, str] | None = None
    template: TemplateExportMeta
    canvas_data: dict[str, Any]
    assets: list[AssetExport] = Field(default_factory=list, max_length=20)


class AssetDupReport(BaseModel):
    """For each incoming asset, whether the user already has a byte-identical
    Asset row — drives the per-duplicate reuse/copy decision on the UI."""

    ref: str
    sha256: str
    matches_existing: bool
    existing_asset_id: int | None = None
    existing_filename: str | None = None


class ObjectSummary(BaseModel):
    """One-line preview of a canvas object for the import wizard's checklist."""

    id: str
    type: str
    label: str
    has_dynamic: bool


class ImportPreview(BaseModel):
    template_name: str
    width_mm: float
    height_mm: float
    object_summary: list[ObjectSummary]
    asset_duplicates: list[AssetDupReport]
    warnings: list[str]


class ImportOptions(BaseModel):
    """User-controlled choices applied at import time. All optional —
    omitting everything yields a faithful import of the source file."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    width_mm: float | None = Field(default=None, gt=0, le=2000)
    height_mm: float | None = Field(default=None, gt=0, le=2000)
    skip_object_ids: list[str] = Field(default_factory=list)
    asset_resolution: dict[str, Literal["reuse", "new"]] = Field(default_factory=dict)


class ImportRequest(BaseModel):
    source: TemplateExport
    options: ImportOptions = Field(default_factory=ImportOptions)
