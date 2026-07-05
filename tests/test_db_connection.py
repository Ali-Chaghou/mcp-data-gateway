"""Tests for the database access layer (db.py).

Unit tests use a fake connection so they need no running database: they pin the
behavior that happens *before and around* the driver call — guard enforcement,
row-limit application, parameter binding, and session setup.

The integration test at the bottom requires the Docker Compose PostgreSQL
instance (`make up`) and stays skipped until the DB setup (M2) lands.
"""

from typing import Any

import psycopg
import pytest

from integration_utils import requires_integration
from mcp_data_gateway import db
from mcp_data_gateway.config import Settings, load_settings
from mcp_data_gateway.security.readonly_sql import ReadOnlyViolation

_PROBE_INSERT = (
    "INSERT INTO passengers (passenger_id, survived, pclass, name, sex, sibsp, parch) "
    "VALUES (999901, 0, 3, 'read-only probe', 'male', 0, 0)"
)

SETTINGS = Settings(
    database_url="postgresql://reader:pw@localhost:5432/agentdata",
    max_rows=200,
    statement_timeout_ms=5000,
)


class _FakeCursor:
    def __init__(self, rows: list[dict[str, Any]], log: list[tuple[str, Any]]) -> None:
        self._rows = rows
        self._log = log

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def execute(self, query: str, params: Any = None) -> None:
        self._log.append((query, params))

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeConnection:
    """Records every executed (query, params) pair; returns preset rows."""

    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []
        self.executed: list[tuple[str, Any]] = []

    def cursor(self, row_factory: Any = None) -> _FakeCursor:
        return _FakeCursor(self.rows, self.executed)


def test_invalid_sql_is_rejected_before_execution() -> None:
    conn = _FakeConnection()
    with pytest.raises(ReadOnlyViolation):
        db.execute_readonly(SETTINGS, "DELETE FROM passengers", conn=conn)
    assert conn.executed == []  # never reached the driver


def test_row_limit_is_applied() -> None:
    conn = _FakeConnection(rows=[{"name": "Alice"}])
    rows = db.execute_readonly(SETTINGS, "SELECT name FROM passengers", conn=conn)
    query, _ = conn.executed[0]
    assert query == "SELECT name FROM passengers LIMIT 200"
    assert rows == [{"name": "Alice"}]


def test_row_limit_clamps_oversized_limit() -> None:
    conn = _FakeConnection()
    db.execute_readonly(SETTINGS, "SELECT * FROM passengers LIMIT 9999", conn=conn)
    query, _ = conn.executed[0]
    assert query == "SELECT * FROM passengers LIMIT 200"


def test_parameters_are_passed_separately_from_sql() -> None:
    conn = _FakeConnection()
    db.execute_readonly(
        SETTINGS,
        "SELECT name FROM passengers WHERE pclass = %s",
        (3,),
        conn=conn,
    )
    query, params = conn.executed[0]
    assert "%s" in query  # placeholder is still in the SQL text
    assert params == (3,)  # value is bound separately, not interpolated


def test_session_setup_forces_read_only_and_timeout() -> None:
    conn = _FakeConnection()
    db._configure_session(conn, SETTINGS)
    queries = [q for q, _ in conn.executed]
    assert any("default_transaction_read_only" in q for q in queries)
    timeout_calls = [(q, p) for q, p in conn.executed if "statement_timeout" in q]
    assert timeout_calls == [("SELECT set_config('statement_timeout', %s, false)", ("5000",))]


@requires_integration
def test_connection_is_read_only() -> None:
    """The configured session must refuse writes even at the driver level.

    With ``default_transaction_read_only = on`` (and the SELECT-only role), an
    INSERT sent straight to the driver — bypassing the guard — must still fail,
    while reads keep working.
    """
    settings = load_settings()
    conn = db.connect(settings)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM passengers")
            row = cur.fetchone()
            assert row is not None and row[0] >= 1
        with conn.cursor() as cur, pytest.raises(psycopg.Error):
            cur.execute(_PROBE_INSERT)
    finally:
        conn.close()
