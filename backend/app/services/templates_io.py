"""Template import / export — bundle a Template + its image assets into a
self-contained JSON file (.blg-template.json), and unpack one back into a
new Template owned by the importing user.

Schema id: "blg-template/v1" — see schemas/template.py:EXPORT_SCHEMA_ID.
Future-breaking changes bump the version; minor additions stay v1 and
guard new keys with `.get(...)` so older importers don't choke.

Image assets are embedded as base64 inside the JSON. This trades file
size for portability — one file, no zip handling, trivial to inspect.
Hard cap: 5 MB per image, 20 images per template (matches asset upload
limits today).
"""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import secrets
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.label_format import LabelFormat
from app.models.template import Template
from app.models.user import User
from app.schemas.template import (
    EXPORT_SCHEMA_ID,
    AssetDupReport,
    AssetExport,
    FormatHint,
    ImportOptions,
    ImportPreview,
    ObjectSummary,
    TemplateExport,
    TemplateExportMeta,
)
from app.services import assets as assets_svc
from app.services import templates as tpl_svc

_PLACEHOLDER_MARKER = "{{"


class TemplateExportError(ValueError):
    pass


class TemplateImportError(ValueError):
    pass


# ---------------- export ----------------


def _new_asset_ref() -> str:
    """Short opaque token bundled with each asset — stable only inside one
    file. Not a hash; renderer never trusts user input that looks like one."""
    return f"asset-{secrets.token_hex(4)}"


def export_template(session: Session, template_id: int, user: User) -> dict[str, Any]:
    """Build the JSON-serializable export payload for a Template.

    Replaces every `image` object's `assetId` (DB primary key, meaningless
    elsewhere) with an `assetRef` that points into the bundled `assets[]`
    array. Reads each referenced Asset's binary from disk and base64-encodes
    it inline.
    """
    try:
        tpl = tpl_svc.get(session, template_id, requesting_user_id=user.id)
    except tpl_svc.TemplateNotFoundError as exc:
        raise TemplateExportError(f"template {template_id} not found") from exc
    except tpl_svc.TemplateAccessError as exc:
        raise TemplateExportError(f"template {template_id} not accessible") from exc

    canvas = deepcopy(tpl.canvas_data) if tpl.canvas_data else {"version": 1, "objects": []}

    # Collect referenced assets — one entry per distinct assetId, in first-
    # encounter order so the export is deterministic.
    asset_id_to_ref: dict[int, str] = {}
    bundled_assets: list[AssetExport] = []
    for obj in canvas.get("objects", []) or []:
        if obj.get("type") != "image":
            continue
        asset_id = obj.get("assetId")
        if not isinstance(asset_id, int):
            continue
        if asset_id not in asset_id_to_ref:
            asset = session.get(Asset, asset_id)
            if asset is None or asset.owner_id != tpl.owner_id:
                # Skip orphaned references rather than blowing up — the
                # editor would already render this as a broken image.
                continue
            ref = _new_asset_ref()
            asset_id_to_ref[asset_id] = ref
            bundled_assets.append(_export_asset(asset, ref))
        # Rewrite the canvas reference in-place
        obj["assetRef"] = asset_id_to_ref[asset_id]
        obj.pop("assetId", None)

    fmt = tpl.format
    format_hint = (
        FormatHint(
            name=fmt.name,
            width_mm=float(fmt.width_mm),
            height_mm=float(fmt.height_mm),
        )
        if fmt is not None
        else None
    )

    payload = TemplateExport(
        **{"$schema": EXPORT_SCHEMA_ID},
        exportedAt=datetime.now(UTC),
        exportedBy=user.email,
        exporter={"app": "BarcodeLabelGen", "version": "0.1.0"},
        template=TemplateExportMeta(
            name=tpl.name,
            description=tpl.description,
            width_mm=float(tpl.width_mm),
            height_mm=float(tpl.height_mm),
            format_hint=format_hint,
        ),
        canvas_data=canvas,
        assets=bundled_assets,
    )
    return payload.model_dump(mode="json", by_alias=True)


def _export_asset(asset: Asset, ref: str) -> AssetExport:
    """Read the on-disk binary, base64-encode it, compute sha256 if missing."""
    path = assets_svc.assets_dir() / asset.storage_filename
    if not path.is_file():
        raise TemplateExportError(f"asset {asset.id} file missing on disk")
    raw = path.read_bytes()
    sha = asset.sha256 or hashlib.sha256(raw).hexdigest()
    return AssetExport(
        ref=ref,
        original_filename=asset.original_filename,
        mime_type=asset.mime_type,
        width_px=asset.width_px,
        height_px=asset.height_px,
        size_bytes=len(raw),
        sha256=sha,
        data_b64=base64.b64encode(raw).decode("ascii"),
    )


# ---------------- preview ----------------


def preview_import(session: Session, source: TemplateExport, user: User) -> ImportPreview:
    """Pre-flight check before the actual import: report each canvas object
    + each asset's duplicate status against the user's existing library."""
    _validate_canvas_assets(source)

    objects = source.canvas_data.get("objects", []) or []
    object_summary = [_object_summary(o) for o in objects]

    asset_duplicates: list[AssetDupReport] = []
    for asset in source.assets:
        existing = assets_svc.find_by_sha256(session, owner_id=user.id, sha256=asset.sha256)
        asset_duplicates.append(
            AssetDupReport(
                ref=asset.ref,
                sha256=asset.sha256,
                matches_existing=existing is not None,
                existing_asset_id=existing.id if existing else None,
                existing_filename=existing.original_filename if existing else None,
            )
        )

    warnings: list[str] = []
    hint = source.template.format_hint
    if hint is not None and _find_format_by_name(session, hint.name) is None:
        warnings.append(
            f"Format '{hint.name}' not found on this instance — will fall back to Custom."
        )

    return ImportPreview(
        template_name=source.template.name,
        width_mm=source.template.width_mm,
        height_mm=source.template.height_mm,
        object_summary=object_summary,
        asset_duplicates=asset_duplicates,
        warnings=warnings,
    )


def _object_summary(obj: dict[str, Any]) -> ObjectSummary:
    """Compact one-line label for the import wizard's checkbox row."""
    kind = obj.get("type", "?")
    obj_id = str(obj.get("id", ""))
    if kind == "text":
        text = str(obj.get("text", ""))
        label = f"Text: {text[:40]}{'…' if len(text) > 40 else ''}"
    elif kind == "barcode":
        label = f"Barcode: {obj.get('barcodeType', '?')} ({str(obj.get('data', ''))[:30]})"
    elif kind == "image":
        label = "Image"
    elif kind == "rect":
        label = "Rectangle"
    elif kind == "line":
        label = "Line"
    elif kind == "table":
        label = f"Table {obj.get('rows', '?')}×{obj.get('cols', '?')}"
    else:
        label = kind
    has_dynamic = _has_placeholder(obj)
    return ObjectSummary(id=obj_id, type=kind, label=label, has_dynamic=has_dynamic)


def _has_placeholder(obj: dict[str, Any]) -> bool:
    """True if the object contains a `{{...}}` placeholder anywhere a series
    substitution would land (text content or barcode data)."""
    for field in ("text", "data"):
        v = obj.get(field)
        if isinstance(v, str) and _PLACEHOLDER_MARKER in v:
            return True
    cells = obj.get("cells")
    if isinstance(cells, list):
        for row in cells:
            if isinstance(row, list) and any(
                isinstance(c, str) and _PLACEHOLDER_MARKER in c for c in row
            ):
                return True
    return False


# ---------------- import ----------------


def import_template(
    session: Session,
    source: TemplateExport,
    options: ImportOptions,
    user: User,
) -> Template:
    """Materialize a TemplateExport into a new Template owned by `user`.

    Walks the canvas in three passes:
      1. filter out skipped object ids;
      2. for every remaining `image` object, decide reuse/new for its
         bundled asset, write to disk if new, build a ref→asset_id map;
      3. rewrite assetRef → assetId on the canvas objects.

    Then resolves the target dimensions + LabelFormat and delegates to
    the existing `tpl_svc.create()` so the rest of the create pipeline
    (validation, version=1, autosave hook) stays one code path.
    """
    _validate_canvas_assets(source)

    objects_in = source.canvas_data.get("objects", []) or []
    skip_set = set(options.skip_object_ids)
    objects_kept = [o for o in objects_in if str(o.get("id", "")) not in skip_set]

    # Validate that every id in skip_object_ids actually existed in the
    # source — otherwise the UI is letting through a stale form state.
    known_ids = {str(o.get("id", "")) for o in objects_in}
    unknown = [oid for oid in options.skip_object_ids if oid not in known_ids]
    if unknown:
        raise TemplateImportError(f"unknown object ids in skip list: {unknown}")

    # Asset map: keyed by ref from the source bundle. We only materialize
    # assets actually used by the kept objects — skipping the rect that
    # referenced an image, for example, means that image isn't created.
    used_refs = {
        str(o.get("assetRef"))
        for o in objects_kept
        if o.get("type") == "image" and o.get("assetRef")
    }
    src_assets_by_ref = {a.ref: a for a in source.assets}
    for ref in used_refs:
        if ref not in src_assets_by_ref:
            raise TemplateImportError(
                f"object references missing asset '{ref}'; export file is corrupted"
            )

    ref_to_new_id: dict[str, int] = {}
    for ref in used_refs:
        src_asset = src_assets_by_ref[ref]
        resolution = options.asset_resolution.get(ref, "new")
        if resolution == "reuse":
            existing = assets_svc.find_by_sha256(
                session, owner_id=user.id, sha256=src_asset.sha256
            )
            if existing is None:
                # UI offered "reuse" based on stale preview data, or the
                # asset was deleted between preview and submit — fall
                # through and create a fresh copy rather than error.
                resolution = "new"
            else:
                ref_to_new_id[ref] = existing.id
                continue
        # "new" path: decode, validate hash, create Asset
        raw = _decode_asset(src_asset)
        new_asset = assets_svc.save_image_from_bytes(
            session,
            owner_id=user.id,
            original_filename=src_asset.original_filename,
            raw=raw,
            declared_mime=src_asset.mime_type,
        )
        ref_to_new_id[ref] = new_asset.id

    # Rewrite kept objects: assetRef → assetId. Deep-copy so we never
    # mutate the request payload (which Pydantic also still holds onto).
    objects_out = []
    for obj in objects_kept:
        new_obj = copy.deepcopy(obj)
        if new_obj.get("type") == "image":
            ref = new_obj.pop("assetRef", None)
            if ref is not None:
                if ref not in ref_to_new_id:
                    # Defensive: shouldn't happen because used_refs covers it.
                    raise TemplateImportError(f"asset ref '{ref}' not resolved")
                new_obj["assetId"] = ref_to_new_id[ref]
        objects_out.append(new_obj)

    final_w = float(options.width_mm) if options.width_mm is not None else float(source.template.width_mm)
    final_h = float(options.height_mm) if options.height_mm is not None else float(source.template.height_mm)

    canvas_out = {
        "version": int(source.canvas_data.get("version", 1)),
        "stage": {"width_mm": final_w, "height_mm": final_h},
        "objects": objects_out,
    }

    # Resolve target LabelFormat:
    #   1. If the source's format_hint name matches one on this instance, use it.
    #   2. Otherwise fall back to the seeded "Custom" format (migration 0004).
    format_id = _resolve_format_id(session, source.template.format_hint)

    desired_name = (options.name or source.template.name).strip()
    final_name = _disambiguate_name(session, user.id, desired_name)

    return tpl_svc.create(
        session,
        owner_id=user.id,
        name=final_name,
        description=source.template.description,
        format_id=format_id,
        canvas_data=canvas_out,
        width_mm=final_w,
        height_mm=final_h,
    )


def _decode_asset(src: AssetExport) -> bytes:
    """Base64-decode + verify against the bundled sha256. Refuses if the
    hash disagrees — tampered files shouldn't be silently accepted."""
    try:
        raw = base64.b64decode(src.data_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise TemplateImportError(f"asset '{src.ref}': base64 decode failed") from exc
    if len(raw) > 5 * 1024 * 1024:
        raise TemplateImportError(f"asset '{src.ref}': decoded size exceeds 5 MB cap")
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != src.sha256:
        raise TemplateImportError(
            f"asset '{src.ref}': sha256 mismatch (file claims {src.sha256[:8]}…, "
            f"actual {actual_sha[:8]}…)"
        )
    return raw


def _resolve_format_id(session: Session, hint: FormatHint | None) -> int:
    """Bind to a name-matching format if possible, otherwise the system
    "Custom" row. Raises if Custom is unexpectedly missing (would mean
    migration 0004 hasn't run on this DB)."""
    if hint is not None:
        match = _find_format_by_name(session, hint.name)
        if match is not None:
            return match.id
    custom = _find_format_by_name(session, "Custom (define size)")
    if custom is None:
        raise TemplateImportError("Custom system format missing — DB not migrated?")
    return custom.id


def _find_format_by_name(session: Session, name: str) -> LabelFormat | None:
    return session.execute(
        select(LabelFormat).where(LabelFormat.name == name).limit(1)
    ).scalar_one_or_none()


def _disambiguate_name(session: Session, owner_id: int, desired: str) -> str:
    """If the user already has a template with this name, append " (kopia)"
    (or " (kopia N)") so the new row is visibly distinct in the list."""
    existing = set(
        session.execute(select(Template.name).where(Template.owner_id == owner_id)).scalars()
    )
    if desired not in existing:
        return desired
    base = f"{desired} (kopia)"
    if base not in existing:
        return base
    n = 2
    while f"{desired} (kopia {n})" in existing:
        n += 1
    return f"{desired} (kopia {n})"


def _validate_canvas_assets(source: TemplateExport) -> None:
    """Cross-field checks Pydantic alone can't express:
      - every `image` object's assetRef must point into source.assets,
      - sanity cap on object count (50)."""
    objects = source.canvas_data.get("objects", []) or []
    if not isinstance(objects, list):
        raise TemplateImportError("canvas_data.objects must be a list")
    if len(objects) > 50:
        raise TemplateImportError(f"too many objects: {len(objects)} (max 50)")

    refs_in_assets = {a.ref for a in source.assets}
    for obj in objects:
        if obj.get("type") != "image":
            continue
        ref = obj.get("assetRef")
        if not isinstance(ref, str) or not ref:
            raise TemplateImportError("image object missing assetRef")
        if ref not in refs_in_assets:
            raise TemplateImportError(f"image object references unknown asset '{ref}'")
