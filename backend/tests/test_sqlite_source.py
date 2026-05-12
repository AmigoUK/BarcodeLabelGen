"""Unit tests for the SQLite-as-data-source service.

These tests don't go through Flask — they exercise sqlite_source directly
on real on-disk SQLite files in a tmp_path. The validator and RO behaviour
are pure functions of the file + query, so this is the right level.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.services import sqlite_source as ss


def _make_db(path: Path) -> Path:
    """Create a tiny SQLite file with two tables for the tests below."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE products (sku TEXT, name TEXT, price REAL);
        INSERT INTO products VALUES ('A001', 'Apple',  1.50);
        INSERT INTO products VALUES ('A002', 'Banana', 0.75);
        INSERT INTO products VALUES ('A003', 'Cherry', 3.20);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, sku TEXT, qty INTEGER);
        INSERT INTO orders (sku, qty) VALUES ('A001', 5), ('A002', 2);
        """
    )
    conn.commit()
    conn.close()
    return path


# ---------------- validator ----------------


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM products",
        "SELECT sku, name FROM products WHERE price > 1",
        "  SELECT 1  ",
        "SELECT 1;",  # trailing semicolon is normalized away
        "SELECT 1;;;",
        "WITH cte AS (SELECT 1 AS x) SELECT * FROM cte",
        "select * from products",  # case-insensitive leading SELECT
    ],
)
def test_validate_select_accepts_valid_queries(sql: str) -> None:
    cleaned = ss.validate_select(sql)
    assert cleaned.lower().lstrip().startswith(("select", "with"))


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO products VALUES ('x','y',0)",
        "DELETE FROM products",
        "UPDATE products SET price = 0",
        "DROP TABLE products",
        "ATTACH DATABASE 'x' AS y",
        "PRAGMA table_info(products)",
        "VACUUM",
        "REINDEX products",
        "ALTER TABLE products RENAME TO p",
        "SELECT 1; DELETE FROM products",  # multi-statement
        "SELECT 1; SELECT 2",  # multi-statement even if both SELECT
        "EXPLAIN SELECT * FROM products",  # not a leading SELECT
        "",  # empty
        "   ",  # whitespace-only
        ";",  # only a semicolon
    ],
)
def test_validate_select_rejects_dangerous_input(sql: str) -> None:
    with pytest.raises(ss.SqliteSourceError):
        ss.validate_select(sql)


def test_validate_select_oversize_query_rejected() -> None:
    big = "SELECT '" + ("x" * (ss.MAX_QUERY_LEN + 100)) + "'"
    with pytest.raises(ss.SqliteSourceError):
        ss.validate_select(big)


# ---------------- read-only enforcement ----------------


def test_open_readonly_blocks_writes(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "t.db")
    with ss.open_readonly(db) as conn:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("INSERT INTO products VALUES ('Z','Z',0)")


def test_open_readonly_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ss.SqliteSourceError):
        ss.open_readonly(tmp_path / "no-such-file.db")


def test_is_valid_sqlite_file(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "t.db")
    assert ss.is_valid_sqlite_file(db) is True

    bogus = tmp_path / "bogus.db"
    bogus.write_bytes(b"not a sqlite file at all, just random bytes")
    assert ss.is_valid_sqlite_file(bogus) is False


# ---------------- table introspection ----------------


def test_list_tables_returns_columns_and_row_counts(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "t.db")
    tables = ss.list_tables(db)
    by_name = {t.name: t for t in tables}
    assert set(by_name) == {"products", "orders"}
    assert by_name["products"].columns == ["sku", "name", "price"]
    assert by_name["products"].row_count == 3
    assert by_name["orders"].row_count == 2


def test_list_tables_skips_sqlite_internals(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "t.db")
    # Adding a regular table is enough to confirm sqlite_master / sqlite_sequence
    # are filtered out by the WHERE clause.
    tables = ss.list_tables(db)
    assert all(not t.name.startswith("sqlite_") for t in tables)


# ---------------- execute_table / execute_query ----------------


def test_execute_table_returns_str_dicts(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "t.db")
    rows = ss.execute_table(db, "products")
    assert len(rows) == 3
    assert rows[0] == {"sku": "A001", "name": "Apple", "price": "1.5"}
    # Every value is a string — matches CSV/XLSX path.
    assert all(isinstance(v, str) for r in rows for v in r.values())


def test_execute_table_unknown_name_raises(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "t.db")
    with pytest.raises(ss.SqliteSourceError):
        ss.execute_table(db, "no_such_table")


def test_execute_query_runs_validated_select(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "t.db")
    rows = ss.execute_query(db, "SELECT sku, UPPER(name) AS name FROM products WHERE price > 1")
    assert [r["name"] for r in rows] == ["APPLE", "CHERRY"]


def test_execute_query_propagates_validator_errors(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "t.db")
    # DELETE is rejected at the leading-keyword check (not even SELECT).
    with pytest.raises(ss.SqliteSourceError):
        ss.execute_query(db, "DELETE FROM products")
    # A leading SELECT that *contains* a forbidden keyword hits the block-list.
    with pytest.raises(ss.SqliteSourceError, match="forbidden"):
        ss.execute_query(db, "SELECT 1 UPDATE products SET price = 0")


def test_execute_query_propagates_sqlite_errors(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "t.db")
    with pytest.raises(ss.SqliteSourceError, match="query failed"):
        ss.execute_query(db, "SELECT * FROM no_such_table")


# ---------------- row-cap enforcement ----------------


def test_execute_table_rejects_over_max_rows(tmp_path: Path) -> None:
    db = tmp_path / "big.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE big (n INTEGER)")
    conn.executemany("INSERT INTO big VALUES (?)", [(i,) for i in range(ss.MAX_ROWS + 1)])
    conn.commit()
    conn.close()

    with pytest.raises(ss.SqliteSourceError, match="row limit"):
        ss.execute_table(db, "big")


# ---------------- snapshot ----------------


def test_snapshot_via_table(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "t.db")
    cols, n = ss.snapshot(db, table="products", query=None)
    assert cols == ["sku", "name", "price"]
    assert n == 3


def test_snapshot_via_query(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "t.db")
    cols, n = ss.snapshot(db, table=None, query="SELECT sku, name FROM products WHERE price > 1")
    assert cols == ["sku", "name"]
    assert n == 2


def test_snapshot_requires_exactly_one(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "t.db")
    with pytest.raises(ss.SqliteSourceError):
        ss.snapshot(db, table="products", query="SELECT 1")
    with pytest.raises(ss.SqliteSourceError):
        ss.snapshot(db, table=None, query=None)
