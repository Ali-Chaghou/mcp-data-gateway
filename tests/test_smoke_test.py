"""Tests for smoke-test helpers and checks.

These use fake connections so the check functions run without a live database.
The full ``main()`` orchestration is exercised end-to-end by ``make smoke``
against a running stack.
"""

from typing import Any

import psycopg
import pytest

import smoke_test as smoke
from mcp_data_gateway.config import Settings

SETTINGS = Settings(
    database_url="postgresql://reader:pw@localhost:5432/agentdata",
    max_rows=200,
    statement_timeout_ms=5000,
)


class _FakeCursor:
    def __init__(self, rows: list[dict[str, Any]], raise_on_execute: bool) -> None:
        self._rows = rows
        self._raise = raise_on_execute

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def execute(self, query: str, params: Any = None) -> None:
        if self._raise:
            raise psycopg.Error("permission denied for table passengers")

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeConnection:
    def __init__(
        self, rows: list[dict[str, Any]] | None = None, *, raise_on_execute: bool = False
    ) -> None:
        self.rows = [] if rows is None else rows
        self._raise = raise_on_execute

    def cursor(self, row_factory: Any = None) -> _FakeCursor:
        return _FakeCursor(self.rows, self._raise)


# --- helpers --------------------------------------------------------------


def test_setup_message_lists_the_recovery_commands() -> None:
    msg = smoke.setup_message("database not up")
    assert "database not up" in msg
    for cmd in ("cp .env.example .env", "make up", "make load-data"):
        assert cmd in msg


def test_short_returns_first_line_only() -> None:
    exc = psycopg.Error("connection refused\nmore detail\nand more")
    assert smoke._short(exc) == "connection refused"


def test_short_falls_back_to_type_name_for_empty_message() -> None:
    assert smoke._short(psycopg.Error("")) == "Error"


# --- checks: passing paths ------------------------------------------------


def test_check_list_tables_passes() -> None:
    smoke.check_list_tables(SETTINGS, _FakeConnection())  # must not raise


def test_check_describe_table_passes() -> None:
    smoke.check_describe_table(SETTINGS, _FakeConnection(rows=[{"x": 1}]))


def test_check_get_passenger_passes_with_a_row() -> None:
    smoke.check_get_passenger(SETTINGS, _FakeConnection(rows=[{"passenger_id": 1}]))


def test_check_search_passengers_passes() -> None:
    smoke.check_search_passengers(SETTINGS, _FakeConnection(rows=[]))


def test_check_survival_summary_passes() -> None:
    smoke.check_survival_summary(
        SETTINGS, _FakeConnection(rows=[{"total_count": 10, "survived_count": 4}])
    )


def test_check_survival_by_passes() -> None:
    rows = [{"group_value": "female", "total_count": 5, "survived_count": 3}]
    smoke.check_survival_by(SETTINGS, _FakeConnection(rows=rows))


# --- checks: failing paths ------------------------------------------------


def test_check_get_passenger_fails_when_missing() -> None:
    with pytest.raises(AssertionError):
        smoke.check_get_passenger(SETTINGS, _FakeConnection(rows=[]))


def test_check_write_protection_passes_when_insert_refused() -> None:
    conn = _FakeConnection(raise_on_execute=True)
    smoke.check_write_protection(SETTINGS, conn)  # refused write is the success case


def test_check_write_protection_fails_when_insert_succeeds() -> None:
    conn = _FakeConnection(raise_on_execute=False)
    with pytest.raises(AssertionError):
        smoke.check_write_protection(SETTINGS, conn)


# --- run_checks aggregation -----------------------------------------------


def test_run_checks_reports_failures(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def ok(settings: Settings, conn: Any) -> None:
        pass

    def bad(settings: Settings, conn: Any) -> None:
        raise AssertionError("boom")

    monkeypatch.setattr(smoke, "CHECKS", [("good one", ok), ("bad one", bad)])
    failures = smoke.run_checks(SETTINGS, _FakeConnection())
    assert failures == ["bad one"]
    out = capsys.readouterr().out
    assert "ok    good one" in out
    assert "FAIL  bad one: boom" in out
