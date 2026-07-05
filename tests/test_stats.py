"""Tests for the aggregate statistics tools.

Unit tests use a fake connection so they exercise the real
``db.execute_readonly`` path (guard + row limit) without a live database.
"""

from typing import Any

import pytest

import load_titanic as loader
from integration_utils import requires_integration
from mcp_data_gateway.config import Settings, load_settings
from mcp_data_gateway.tools.stats import (
    ALLOWED_GROUP_BY,
    InvalidGroupByError,
    survival_by,
    survival_summary,
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
        self.rows = [] if rows is None else rows
        self.executed: list[tuple[str, Any]] = []

    def cursor(self, row_factory: Any = None) -> _FakeCursor:
        return _FakeCursor(self.rows, self.executed)


# --- survival_summary -----------------------------------------------------


def test_survival_summary_uses_readonly_layer_and_returns_dict() -> None:
    conn = _FakeConnection(rows=[{"total_count": 10, "survived_count": 4}])
    result = survival_summary(SETTINGS, conn=conn)
    assert len(conn.executed) == 1  # went through execute_readonly
    assert result == {"total_count": 10, "survived_count": 4, "survival_rate": 0.4}


def test_survival_summary_handles_empty_table() -> None:
    conn = _FakeConnection(rows=[{"total_count": 0, "survived_count": None}])
    result = survival_summary(SETTINGS, conn=conn)
    assert result == {"total_count": 0, "survived_count": 0, "survival_rate": 0.0}


# --- survival_by: allowed group_by ----------------------------------------


@pytest.mark.parametrize("group_by", ALLOWED_GROUP_BY)
def test_survival_by_accepts_allowed_group_by(group_by: str) -> None:
    conn = _FakeConnection(rows=[{"group_value": "x", "total_count": 5, "survived_count": 3}])
    result = survival_by(SETTINGS, group_by, conn=conn)
    query, _ = conn.executed[0]
    assert f"GROUP BY {group_by}" in query
    assert result == [{"group": "x", "total_count": 5, "survived_count": 3, "survival_rate": 0.6}]


def test_survival_by_output_shape_is_stable() -> None:
    conn = _FakeConnection(
        rows=[
            {"group_value": 1, "total_count": 4, "survived_count": 1},
            {"group_value": 2, "total_count": 6, "survived_count": 3},
        ]
    )
    result = survival_by(SETTINGS, "pclass", conn=conn)
    assert [r["group"] for r in result] == [1, 2]
    for row in result:
        assert row.keys() == {"group", "total_count", "survived_count", "survival_rate"}


# --- survival_by: rejected group_by ---------------------------------------


@pytest.mark.parametrize(
    "group_by",
    ["name", "age", "passengers", "pclass; DROP TABLE passengers", "GROUP BY", "", "survived"],
)
def test_survival_by_rejects_unknown_group_by_before_sql(group_by: str) -> None:
    conn = _FakeConnection()
    with pytest.raises(InvalidGroupByError):
        survival_by(SETTINGS, group_by, conn=conn)
    assert conn.executed == []  # rejected before any SQL is issued


def test_group_by_value_is_never_interpolated() -> None:
    conn = _FakeConnection(rows=[{"group_value": "S", "total_count": 3, "survived_count": 1}])
    survival_by(SETTINGS, "embarked", conn=conn)
    query, params = conn.executed[0]
    # The executed query is exactly the fixed template (plus the appended limit),
    # carrying no caller-derived fragments and no bound params.
    assert query.startswith(
        "SELECT embarked AS group_value, count(*) AS total_count, "
        "sum(survived) AS survived_count FROM passengers GROUP BY embarked ORDER BY embarked"
    )
    assert params == ()


@requires_integration
def test_stats_against_live_database() -> None:
    """survival_summary and survival_by run against the real table via gateway_reader."""
    settings = load_settings()

    summary = survival_summary(settings)
    assert summary.keys() == {"total_count", "survived_count", "survival_rate"}
    assert summary["total_count"] == len(loader.SAMPLE_PASSENGERS)
    assert 0.0 <= summary["survival_rate"] <= 1.0

    by_sex = survival_by(settings, "sex")
    groups = {row["group"] for row in by_sex}
    assert {"male", "female"} <= groups
