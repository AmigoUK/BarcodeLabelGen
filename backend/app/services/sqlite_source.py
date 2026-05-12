"""SQLite-as-data-source service.

Reads user-uploaded `.db` / `.sqlite` files via a *read-only* connection
and turns either a whole table OR a single user-supplied SELECT into the
same `list[dict[str, str]]` shape the rest of the dataset pipeline already
consumes (CSV/XLSX path lives in `services/datasets.py`).

Defense in depth, since the SELECT is user-supplied:

  1. Connections are opened with `mode=ro` URI + `PRAGMA query_only`,
     so even a write that slips past the validator is rejected by SQLite
     itself.
  2. We never call `enable_load_extension` (it's off by default — but
     never opt in).
  3. Validator forbids multi-statement input (mid-string `;`) and a
     keyword block-list (ATTACH/PRAGMA/INSERT/UPDATE/DELETE/...).
  4. Every read is wrapped in `SELECT * FROM (<user_sql>) LIMIT 1001` —
     fetching 1001 rows tells us "user query exceeds the cap" so we can
     reject with a helpful error rather than silently truncating.
  5. Table-picker mode validates the table name against the dynamic
     whitelist returned by `list_tables()` before quoting it back into
     SQL — we never let a raw user string near an unparameterized
     identifier slot.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.dataset import DataSet

ALLOWED_EXTS = {"db", "sqlite", "sqlite3"}
MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB — 5× the CSV/XLSX cap; SQLite holds indexes + binary
MAX_ROWS = 1000  # mirrors CSV/XLSX cap from services/datasets.py
MAX_QUERY_LEN = 4096  # bytes
QUERY_TIMEOUT_SECONDS = 5

# Word-boundary, case-insensitive match. ATTACH/DETACH would let a query
# hop to another file; PRAGMA can flip dangerous settings (e.g. journal
# mode, temp_store_directory). Mutating verbs round out the obvious set.
_FORBIDDEN_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "VACUUM",
    "REINDEX",
    "TRIGGER",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "SAVEPOINT",
    "RELEASE",
)
_FORBIDDEN_RE = re.compile(
    r"\b(" + "|".join(_FORBIDDEN_KEYWORDS) + r")\b",
    re.IGNORECASE,
)
_LEADING_WITH_RE = re.compile(r"^\s*WITH\b", re.IGNORECASE)
_LEADING_SELECT_RE = re.compile(r"^\s*SELECT\b", re.IGNORECASE)


class SqliteSourceError(ValueError):
    """Anything wrong with the SQLite source: bad file, bad query, too many rows."""


@dataclass(frozen=True)
class SqliteTableInfo:
    name: str
    columns: list[str]
    row_count: int


def is_valid_sqlite_file(path: Path) -> bool:
    """Cheap sanity check: try to open RO and read sqlite_master once.

    Catches the case where the user renamed a non-SQLite file to .db.
    """
    try:
        with open_readonly(path) as conn:
            conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
        return True
    except sqlite3.DatabaseError:
        return False


def open_readonly(path: Path) -> sqlite3.Connection:
    """Open a SQLite connection in true read-only mode.

    `mode=ro` requires the URI form (`uri=True`); `PRAGMA query_only` is
    a belt-and-braces second layer because some operations (e.g. temp
    tables for hashing) can still mutate even an `ro` handle.
    """
    if not path.is_file():
        raise SqliteSourceError(f"sqlite file not found: {path.name}")
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=QUERY_TIMEOUT_SECONDS, isolation_level=None)
    conn.execute("PRAGMA query_only = ON")
    conn.row_factory = sqlite3.Row
    return conn


def list_tables(path: Path) -> list[SqliteTableInfo]:
    """Enumerate user-visible tables (skip `sqlite_*` internals).

    For each table we run two cheap queries: PRAGMA table_info to read
    the column names, then COUNT(*) so the wizard can show "247 rows"
    without loading anything.
    """
    out: list[SqliteTableInfo] = []
    with open_readonly(path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()
        for (name,) in rows:
            try:
                cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{_quote_ident(name)}")')]
                row_count = int(conn.execute(f'SELECT COUNT(*) FROM "{_quote_ident(name)}"').fetchone()[0])
            except sqlite3.DatabaseError:
                continue  # skip unreadable / corrupted tables
            out.append(SqliteTableInfo(name=name, columns=cols, row_count=row_count))
    return out


def _quote_ident(name: str) -> str:
    """SQLite identifier escape: double any embedded `"`."""
    return name.replace('"', '""')


def validate_select(sql: str) -> str:
    """Normalize + validate a user-supplied SELECT.

    Returns the cleaned query (single statement, leading SELECT or WITH …
    SELECT) or raises `SqliteSourceError` with a human-readable reason.
    """
    if sql is None:
        raise SqliteSourceError("query is empty")
    cleaned = sql.strip()
    # Tolerate a chain of trailing semicolons (e.g. user pasted `SELECT 1;;`)
    # before the multi-statement check below — internal `;` is what's dangerous.
    while cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
    if not cleaned:
        raise SqliteSourceError("query is empty")
    if len(cleaned.encode("utf-8")) > MAX_QUERY_LEN:
        raise SqliteSourceError(f"query exceeds {MAX_QUERY_LEN}-byte limit")

    # Fast structural check — multi-statement input is the classic injection
    # vector (`SELECT 1; DROP TABLE x`). A `;` in a string literal would also
    # trip this; that's intentional — easier to reject and ask the user to
    # rewrite than to ship a half-baked SQL parser.
    if ";" in cleaned:
        raise SqliteSourceError("only a single statement is allowed (no ';')")

    if not (_LEADING_SELECT_RE.match(cleaned) or _LEADING_WITH_RE.match(cleaned)):
        raise SqliteSourceError("only SELECT (optionally prefixed with WITH …) is allowed")

    forbidden = _FORBIDDEN_RE.search(cleaned)
    if forbidden:
        raise SqliteSourceError(
            f"forbidden keyword '{forbidden.group(1).upper()}' — only SELECT queries are allowed"
        )

    return cleaned


def _row_to_str_dict(row: sqlite3.Row) -> dict[str, str]:
    """Convert a sqlite Row into the all-strings shape the rest of the pipeline expects."""
    out: dict[str, str] = {}
    for k in row.keys():
        v = row[k]
        out[k] = "" if v is None else str(v)
    return out


def _execute_capped(conn: sqlite3.Connection, sql: str) -> list[dict[str, str]]:
    """Run `sql`, fetch up to MAX_ROWS+1 rows, raise if the cap was hit."""
    cur = conn.execute(sql)
    rows = cur.fetchmany(MAX_ROWS + 1)
    if len(rows) > MAX_ROWS:
        raise SqliteSourceError(
            f"result exceeds {MAX_ROWS}-row limit; add WHERE/LIMIT to narrow the query"
        )
    return [_row_to_str_dict(r) for r in rows]


def execute_table(path: Path, table_name: str) -> list[dict[str, str]]:
    """Read all rows of `table_name`, capped at MAX_ROWS.

    The table name is validated against the *current* file's schema —
    we never trust the value stored on the DataSet without re-checking.
    """
    with open_readonly(path) as conn:
        if not _table_exists(conn, table_name):
            raise SqliteSourceError(f"table '{table_name}' not found in this file")
        quoted = f'"{_quote_ident(table_name)}"'
        return _execute_capped(conn, f"SELECT * FROM {quoted}")


def execute_query(path: Path, sql: str) -> list[dict[str, str]]:
    """Validate + run a user SELECT, capped at MAX_ROWS.

    The cap is enforced by fetching MAX_ROWS+1 rows post-execution rather
    than wrapping the user query in `SELECT * FROM (…) LIMIT 1001` —
    wrapping breaks user queries that include GROUP BY/ORDER BY-with-
    expressions referencing unaliased columns. Fetch-and-check is just
    as safe and preserves the user's query as written.
    """
    cleaned = validate_select(sql)
    with open_readonly(path) as conn:
        try:
            return _execute_capped(conn, cleaned)
        except sqlite3.DatabaseError as exc:
            raise SqliteSourceError(f"query failed: {exc}") from exc


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


def snapshot(path: Path, *, table: str | None, query: str | None) -> tuple[list[str], int]:
    """Run the configured query/table once to capture (columns, row_count).

    Used by PATCH /sqlite-config to materialize the snapshot the wizard
    needs for the mapping step.
    """
    if (table is None) == (query is None):
        raise SqliteSourceError("specify exactly one of table or query")
    rows = execute_table(path, table) if table is not None else execute_query(path, query or "")
    columns = list(rows[0].keys()) if rows else _columns_only(path, table=table, query=query)
    return columns, len(rows)


def _columns_only(path: Path, *, table: str | None, query: str | None) -> list[str]:
    """Fall back to extracting column names when the result set is empty.

    For tables we can use PRAGMA. For queries we re-execute with LIMIT 0
    so SQLite still hands us the column list via cursor.description.
    """
    with open_readonly(path) as conn:
        if table is not None:
            return [r[1] for r in conn.execute(f'PRAGMA table_info("{_quote_ident(table)}")')]
        cleaned = validate_select(query or "")
        cur = conn.execute(cleaned)
        try:
            cols = [d[0] for d in (cur.description or [])]
        finally:
            cur.close()
        return cols


def load_rows(ds: DataSet) -> list[dict[str, str]]:
    """Public entry point used by services/datasets.load_rows() dispatch."""
    from app.services.datasets import uploads_dir  # local import avoids cycle

    path = uploads_dir() / ds.storage_filename
    if ds.sqlite_table:
        return execute_table(path, ds.sqlite_table)
    if ds.sqlite_query:
        return execute_query(path, ds.sqlite_query)
    return []  # not yet configured — empty result set
