"""Tests for MCP tool registration and wrapper behavior.

These import the server module (proving import touches neither the environment
nor a database) and exercise the wrappers via monkeypatched settings and tool
functions, so no live database is needed.
"""

import json
import logging
from decimal import Decimal
from typing import Any

import pytest

from mcp_data_gateway import server
from mcp_data_gateway.config import Settings
from mcp_data_gateway.tools import passengers, schema, stats
from mcp_data_gateway.tools.passengers import InvalidFilterError
from mcp_data_gateway.tools.schema import UnknownTableError
from mcp_data_gateway.tools.stats import InvalidGroupByError

SETTINGS = Settings(
    database_url="postgresql://reader:pw@localhost:5432/agentdata",
    max_rows=200,
    statement_timeout_ms=5000,
)

EXPECTED_TOOLS = {
    "list_tables",
    "describe_table",
    "get_passenger",
    "search_passengers",
    "survival_summary",
    "survival_by",
}


@pytest.fixture
def fake_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "_get_settings", lambda: SETTINGS)


def test_all_expected_tools_are_registered() -> None:
    names = {tool.name for tool in server.mcp._tool_manager.list_tools()}
    assert names == EXPECTED_TOOLS


def test_registered_tools_have_descriptions() -> None:
    for tool in server.mcp._tool_manager.list_tools():
        assert tool.description  # populated from each wrapper's docstring


def test_no_arbitrary_sql_tool_is_exposed() -> None:
    names = {tool.name for tool in server.mcp._tool_manager.list_tools()}
    assert not any("sql" in n.lower() or "query" in n.lower() or "exec" in n.lower() for n in names)


def test_list_tables_wrapper_delegates() -> None:
    assert server.list_tables() == ["passengers"]


def test_describe_table_wrapper_passes_settings_and_table(
    fake_settings: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr(schema, "describe_table", lambda s, t: calls.append((s, t)) or {"table": t})
    result = server.describe_table()
    assert calls == [(SETTINGS, "passengers")]
    assert result == {"table": "passengers"}


def test_get_passenger_wrapper_delegates(
    fake_settings: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr(passengers, "get_passenger", lambda s, pid: calls.append((s, pid)) or None)
    assert server.get_passenger(7) is None
    assert calls == [(SETTINGS, 7)]


def test_search_passengers_wrapper_forwards_filters(
    fake_settings: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    def fake(settings: Settings, **kwargs: Any) -> list[dict[str, Any]]:
        captured["settings"] = settings
        captured["kwargs"] = kwargs
        return []

    monkeypatch.setattr(passengers, "search_passengers", fake)
    server.search_passengers(pclass=1, sex="female", limit=5)
    assert captured["settings"] is SETTINGS
    assert captured["kwargs"]["pclass"] == 1
    assert captured["kwargs"]["sex"] == "female"
    assert captured["kwargs"]["limit"] == 5


def test_stats_wrappers_delegate(fake_settings: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stats, "survival_summary", lambda s: {"total_count": 1})
    monkeypatch.setattr(stats, "survival_by", lambda s, g: [{"group": g}])
    assert server.survival_summary() == {"total_count": 1}
    assert server.survival_by("sex") == [{"group": "sex"}]


# Validation errors from the tool modules surface directly (they raise before any
# database access), so the wrappers need no special error handling.


def test_describe_table_wrapper_propagates_unknown_table(fake_settings: None) -> None:
    with pytest.raises(UnknownTableError):
        server.describe_table("users")


def test_get_passenger_wrapper_propagates_invalid_id(fake_settings: None) -> None:
    with pytest.raises(InvalidFilterError):
        server.get_passenger(0)


def test_survival_by_wrapper_propagates_invalid_group_by(fake_settings: None) -> None:
    with pytest.raises(InvalidGroupByError):
        server.survival_by("name")


def test_wrapper_output_is_json_safe(fake_settings: None, monkeypatch: pytest.MonkeyPatch) -> None:
    row = {"passenger_id": 1, "age": Decimal("22"), "fare": Decimal("7.25")}
    monkeypatch.setattr(passengers, "get_passenger", lambda s, pid: row)
    result = server.get_passenger(1)
    assert result == {"passenger_id": 1, "age": 22.0, "fare": 7.25}
    json.dumps(result)  # must not raise — Decimal would


def test_wrapper_emits_audit_log_without_leaking_dsn(
    fake_settings: None, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(passengers, "get_passenger", lambda s, pid: {"passenger_id": 1})
    with caplog.at_level(logging.INFO, logger="mcp_data_gateway.audit"):
        server.get_passenger(1)
    msg = caplog.records[0].message
    assert 'tool="get_passenger"' in msg
    assert "result_count=1" in msg
    assert "postgresql://" not in msg  # the DATABASE_URL never reaches the log
