"""Tests for the agent-facing tools (tools/).

Schema-tool unit tests use a fake connection, so they exercise the real
``db.execute_readonly`` path (guard + row limit) without a live database.
"""

from typing import Any

import pytest

from integration_utils import requires_integration
from mcp_data_gateway.config import Settings, load_settings
from mcp_data_gateway.tools.schema import (
    UnknownTableError,
    describe_table,
    list_tables,
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
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or [{"?column?": 1}]
        self.executed: list[tuple[str, Any]] = []

    def cursor(self, row_factory: Any = None) -> _FakeCursor:
        return _FakeCursor(self.rows, self.executed)


def test_list_tables_returns_only_passengers() -> None:
    assert list_tables() == ["passengers"]


def test_describe_table_returns_curated_columns() -> None:
    conn = _FakeConnection()
    result = describe_table(SETTINGS, "passengers", conn=conn)

    assert result["table"] == "passengers"
    names = [col["name"] for col in result["columns"]]
    assert names[0] == "passenger_id"
    assert set(names) >= {"survived", "pclass", "name", "sex", "age", "embarked"}
    for col in result["columns"]:
        assert col.keys() == {"name", "type", "nullable", "description"}


def test_describe_table_reports_nullability() -> None:
    columns = {c["name"]: c for c in describe_table(SETTINGS, conn=_FakeConnection())["columns"]}
    assert columns["passenger_id"]["nullable"] is False
    assert columns["age"]["nullable"] is True


def test_describe_table_probes_through_the_readonly_layer() -> None:
    conn = _FakeConnection()
    describe_table(SETTINGS, "passengers", conn=conn)
    queries = [q for q, _ in conn.executed]
    assert queries == ["SELECT 1 FROM passengers LIMIT 1"]  # single guarded read


def test_describe_table_rejects_unlisted_table() -> None:
    conn = _FakeConnection()
    with pytest.raises(UnknownTableError):
        describe_table(SETTINGS, "users", conn=conn)
    assert conn.executed == []  # rejected before any SQL is issued


def test_describe_table_rejects_information_schema() -> None:
    with pytest.raises(UnknownTableError):
        describe_table(SETTINGS, "information_schema.columns", conn=_FakeConnection())


@requires_integration
def test_describe_table_against_live_database() -> None:
    """describe_table succeeds against the real passengers table via gateway_reader."""
    settings = load_settings()
    assert list_tables() == ["passengers"]
    meta = describe_table(settings, "passengers")
    names = [col["name"] for col in meta["columns"]]
    assert {"passenger_id", "survived", "sex", "age"} <= set(names)
