"""Dataset parsing, filtering, and previewing.

Uploads land on the `uploads` Docker volume as UUID-named files. The DB
keeps only metadata (columns + row count + path); the heavy lifting
(re-reading the file for preview/filter/generation) goes through pandas
once per request — cheap enough at our 1000-row cap.
"""

from __future__ import annotations

import enum
import io
import os
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import DataSet

ALLOWED_EXT = {"csv", "xls", "xlsx"}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per PROJECT.md §F10
MAX_ROWS = 1000  # MVP cap


class DataSetUploadError(ValueError):
    pass


class FilterOp(enum.StrEnum):
    EQ = "eq"
    NEQ = "neq"
    CONTAINS = "contains"
    GT = "gt"
    LT = "lt"
    EMPTY = "empty"
    NON_EMPTY = "non_empty"


def uploads_dir() -> Path:
    return Path(os.environ.get("UPLOADS_DIR", "/app/uploads"))


def _detect_format(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXT:
        raise DataSetUploadError(f"extension .{ext} not allowed")
    return "csv" if ext == "csv" else "xlsx"


def _read_dataframe(file_path: Path, file_format: str) -> pd.DataFrame:
    if file_format == "csv":
        # `keep_default_na=False` keeps user-supplied empty strings as "" rather
        # than NaN, which is what office users expect: a blank cell stays blank.
        return pd.read_csv(file_path, dtype=str, keep_default_na=False)
    return pd.read_excel(file_path, dtype=str, engine="openpyxl").fillna("")


def save_upload(
    session: Session,
    *,
    owner_id: int,
    original_filename: str,
    raw: bytes,
) -> DataSet:
    if not raw:
        raise DataSetUploadError("empty upload")
    if len(raw) > MAX_SIZE_BYTES:
        raise DataSetUploadError(f"file exceeds {MAX_SIZE_BYTES} bytes limit")

    file_format = _detect_format(original_filename)
    storage_filename = f"{uuid.uuid4().hex}.{file_format}"
    target = uploads_dir() / storage_filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)

    try:
        df = _read_dataframe(target, file_format)
    except Exception as exc:  # noqa: BLE001 — anything could go wrong inside pandas
        target.unlink(missing_ok=True)
        raise DataSetUploadError(f"could not parse file: {exc}") from exc

    if df.empty:
        target.unlink(missing_ok=True)
        raise DataSetUploadError("file contains no data rows")
    if len(df) > MAX_ROWS:
        target.unlink(missing_ok=True)
        raise DataSetUploadError(f"file has {len(df)} rows; max {MAX_ROWS} for one batch")

    columns = [str(c) for c in df.columns]
    ds = DataSet(
        owner_id=owner_id,
        original_filename=original_filename,
        storage_filename=storage_filename,
        file_format=file_format,
        columns=columns,
        row_count=int(len(df)),
        size_bytes=len(raw),
    )
    session.add(ds)
    session.commit()
    session.refresh(ds)
    return ds


def get_dataset(session: Session, dataset_id: int) -> DataSet | None:
    return session.get(DataSet, dataset_id)


def list_user_datasets(session: Session, *, owner_id: int) -> list[DataSet]:
    stmt = select(DataSet).where(DataSet.owner_id == owner_id).order_by(DataSet.uploaded_at.desc())
    return list(session.execute(stmt).scalars().all())


def delete_dataset(session: Session, dataset_id: int) -> None:
    ds = session.get(DataSet, dataset_id)
    if ds is None:
        return
    file_path = uploads_dir() / ds.storage_filename
    file_path.unlink(missing_ok=True)
    session.delete(ds)
    session.commit()


def load_rows(ds: DataSet) -> list[dict[str, str]]:
    """Read the dataset back into a list of plain-string row dicts."""
    file_path = uploads_dir() / ds.storage_filename
    if not file_path.is_file():
        return []
    df = _read_dataframe(file_path, ds.file_format)
    df = df.astype(str)
    return df.to_dict(orient="records")  # type: ignore[no-any-return]


def preview_rows(ds: DataSet, *, limit: int = 5) -> list[dict[str, str]]:
    rows = load_rows(ds)
    return rows[:limit]


def apply_filter(
    rows: list[dict[str, str]],
    *,
    column: str,
    op: FilterOp,
    value: str = "",
) -> list[dict[str, str]]:
    """Filter rows in-memory by a simple column/operator predicate."""
    if column not in (rows[0].keys() if rows else ()):
        return [] if op != FilterOp.EMPTY else rows  # unknown column → no matches

    needle = value.strip()

    def _match(row: dict[str, str]) -> bool:
        cell = (row.get(column) or "").strip()
        if op is FilterOp.EQ:
            return cell == needle
        if op is FilterOp.NEQ:
            return cell != needle
        if op is FilterOp.CONTAINS:
            return needle.lower() in cell.lower()
        if op is FilterOp.EMPTY:
            return cell == ""
        if op is FilterOp.NON_EMPTY:
            return cell != ""
        try:
            cell_n = float(cell)
            needle_n = float(needle)
        except ValueError:
            return False
        if op is FilterOp.GT:
            return cell_n > needle_n
        if op is FilterOp.LT:
            return cell_n < needle_n
        return False

    return [r for r in rows if _match(r)]


def csv_bytes_from_rows(columns: list[str], rows: list[dict[str, Any]]) -> bytes:
    """Helper used by tests — round-trip rows back to CSV bytes."""
    buf = io.StringIO()
    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(buf, index=False)
    return buf.getvalue().encode()
