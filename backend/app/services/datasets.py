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

from app.models.dataset import DataSet, DataSetSourceType
from app.services import sqlite_source

ALLOWED_EXT = {"csv", "xls", "xlsx"}
SQLITE_EXT = sqlite_source.ALLOWED_EXTS  # {"db","sqlite","sqlite3"}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per PROJECT.md §F10 (CSV/XLSX)
MAX_SIZE_BYTES_SQLITE = sqlite_source.MAX_SIZE_BYTES  # 50 MB
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
    """Return canonical file_format token for the extension.

    Tabular extensions normalize to 'csv' / 'xlsx'. SQLite extensions keep
    their literal form ('db' / 'sqlite' / 'sqlite3') — purely informational.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in SQLITE_EXT:
        return ext
    if ext not in ALLOWED_EXT:
        raise DataSetUploadError(f"extension .{ext} not allowed")
    return "csv" if ext == "csv" else "xlsx"


def _source_type_for(file_format: str) -> DataSetSourceType:
    if file_format in SQLITE_EXT:
        return DataSetSourceType.SQLITE
    if file_format == "csv":
        return DataSetSourceType.CSV
    return DataSetSourceType.XLSX


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

    file_format = _detect_format(original_filename)
    source_type = _source_type_for(file_format)

    size_limit = MAX_SIZE_BYTES_SQLITE if source_type is DataSetSourceType.SQLITE else MAX_SIZE_BYTES
    if len(raw) > size_limit:
        raise DataSetUploadError(f"file exceeds {size_limit} bytes limit")

    storage_filename = f"{uuid.uuid4().hex}.{file_format}"
    target = uploads_dir() / storage_filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)

    if source_type is DataSetSourceType.SQLITE:
        # Don't materialize rows yet — the user still has to pick a table or
        # write a SELECT. Just sanity-check that the file actually opens as a
        # SQLite database (caught here so we surface a clean 400, not an
        # opaque crash later in the wizard).
        if not sqlite_source.is_valid_sqlite_file(target):
            target.unlink(missing_ok=True)
            raise DataSetUploadError("file is not a valid SQLite database")
        ds = DataSet(
            owner_id=owner_id,
            original_filename=original_filename,
            storage_filename=storage_filename,
            file_format=file_format,
            source_type=source_type,
            columns=[],
            row_count=0,
            size_bytes=len(raw),
        )
        session.add(ds)
        session.commit()
        session.refresh(ds)
        return ds

    # CSV / XLSX path — parse immediately so the upload response already
    # carries columns + row_count and the wizard can advance to the mapping
    # step without an extra round-trip.
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
        source_type=source_type,
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
    """Read the dataset back into a list of plain-string row dicts.

    Dispatch on source_type so callers don't care which format the user
    uploaded — they always receive `list[dict[str, str]]`.
    """
    if ds.source_type is DataSetSourceType.SQLITE:
        return sqlite_source.load_rows(ds)
    file_path = uploads_dir() / ds.storage_filename
    if not file_path.is_file():
        return []
    df = _read_dataframe(file_path, ds.file_format)
    df = df.astype(str)
    return df.to_dict(orient="records")  # type: ignore[no-any-return]


def configure_sqlite(
    session: Session, ds: DataSet, *, table: str | None, query: str | None
) -> DataSet:
    """Finalize a SQLite-source dataset by selecting a table or storing a SELECT.

    Validates the choice by actually executing it (RO connection + LIMIT
    cap), then persists the resulting columns + row_count snapshot on the
    DataSet so the wizard's mapping step has the metadata it needs.

    Raises `DataSetUploadError` on validation failure (caller turns into 400).
    """
    if ds.source_type is not DataSetSourceType.SQLITE:
        raise DataSetUploadError("sqlite-config only applies to SQLite datasets")

    path = uploads_dir() / ds.storage_filename
    try:
        columns, row_count = sqlite_source.snapshot(path, table=table, query=query)
    except sqlite_source.SqliteSourceError as exc:
        raise DataSetUploadError(str(exc)) from exc

    if row_count == 0:
        # Renderer would have nothing to do — surface this now rather than at /generate
        # so the user can pick a different table without getting halfway through the wizard.
        what = f"table '{table}'" if table else "the SELECT query"
        raise DataSetUploadError(f"{what} returned 0 rows; pick a source with data")

    ds.sqlite_table = table.strip() if table else None
    ds.sqlite_query = query.strip() if query else None
    ds.columns = columns
    ds.row_count = row_count
    session.commit()
    session.refresh(ds)
    return ds


def sqlite_tables_for(ds: DataSet) -> list[sqlite_source.SqliteTableInfo]:
    """Re-read the SQLite file's table list for the wizard's picker."""
    if ds.source_type is not DataSetSourceType.SQLITE:
        return []
    return sqlite_source.list_tables(uploads_dir() / ds.storage_filename)


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
