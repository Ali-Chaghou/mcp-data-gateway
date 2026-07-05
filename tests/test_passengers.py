"""Tests for the passenger lookup tools.

Unit tests use a fake connection so they exercise the real
``db.execute_readonly`` path (guard + row limit) without a live database.
"""

from typing import Any

import pytest

from mcp_data_gateway.config import Settings
from mcp_data_gateway.tools.passengers import (
    InvalidFilterError,
    get_passenger,
    search_passengers,
)

SETTINGS = Settings(
    database_url="postgresql://reader:pw@localhost:5432/agentdata",
    max_rows=200,
    statement_timeout_ms=5000,
)

ALICE = {"passenger_id": 2, "name": "Cumings, Mrs. John Bradley", "sex": "female"}


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


# --- get_passenger --------------------------------------------------------


def test_get_passenger_builds_parameterized_query() -> None:
    conn = _FakeConnection(rows=[ALICE])
    get_passenger(SETTINGS, 2, conn=conn)
    query, params = conn.executed[0]
    assert "WHERE passenger_id = %s" in query
    assert params == (2,)


def test_get_passenger_returns_row_or_none() -> None:
    assert get_passenger(SETTINGS, 2, conn=_FakeConnection(rows=[ALICE])) == ALICE
    assert get_passenger(SETTINGS, 999, conn=_FakeConnection(rows=[])) is None


@pytest.mark.parametrize("bad", [0, -1, 1.5, "2", True, None])
def test_get_passenger_rejects_invalid_id_before_sql(bad: object) -> None:
    conn = _FakeConnection()
    with pytest.raises(InvalidFilterError):
        get_passenger(SETTINGS, bad, conn=conn)  # type: ignore[arg-type]
    assert conn.executed == []


# --- search_passengers: valid filters -------------------------------------


def test_search_supports_valid_filters() -> None:
    conn = _FakeConnection(rows=[ALICE])
    rows = search_passengers(SETTINGS, pclass=1, sex="female", conn=conn)
    query, params = conn.executed[0]
    assert "WHERE pclass = %s AND sex = %s" in query
    assert params == (1, "female")
    assert rows == [ALICE]


def test_search_with_no_filters_selects_all_ordered() -> None:
    conn = _FakeConnection(rows=[ALICE])
    search_passengers(SETTINGS, conn=conn)
    query, params = conn.executed[0]
    assert query.startswith("SELECT * FROM passengers ORDER BY passenger_id")
    assert params == ()


def test_search_age_range_uses_bound_parameters() -> None:
    conn = _FakeConnection()
    search_passengers(SETTINGS, min_age=10, max_age=40, conn=conn)
    query, params = conn.executed[0]
    assert "age >= %s AND age <= %s" in query
    assert params == (10, 40)


def test_search_accepts_bool_for_survived() -> None:
    conn = _FakeConnection()
    search_passengers(SETTINGS, survived=True, conn=conn)
    _, params = conn.executed[0]
    assert params == (1,)  # bool normalized to int


def test_values_are_parameterized_not_interpolated() -> None:
    conn = _FakeConnection()
    search_passengers(SETTINGS, sex="female", embarked="C", conn=conn)
    query, params = conn.executed[0]
    assert "female" not in query and "'C'" not in query
    assert params == ("female", "C")


# --- search_passengers: invalid filters -----------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pclass": 5},
        {"pclass": True},
        {"survived": 2},
        {"sex": "other"},
        {"embarked": "X"},
        {"min_age": -1},
        {"max_age": -5},
        {"min_age": 40, "max_age": 10},
        {"limit": 0},
        {"limit": -3},
        {"limit": 201},  # exceeds settings.max_rows
    ],
)
def test_search_rejects_invalid_filters_before_sql(kwargs: dict[str, Any]) -> None:
    conn = _FakeConnection()
    with pytest.raises(InvalidFilterError):
        search_passengers(SETTINGS, conn=conn, **kwargs)
    assert conn.executed == []


# --- limit behavior -------------------------------------------------------


def test_limit_defaults_to_max_rows() -> None:
    conn = _FakeConnection()
    search_passengers(SETTINGS, conn=conn)
    query, _ = conn.executed[0]
    assert query.endswith("LIMIT 200")


def test_limit_is_applied_when_within_cap() -> None:
    conn = _FakeConnection()
    search_passengers(SETTINGS, limit=5, conn=conn)
    query, _ = conn.executed[0]
    assert query.endswith("LIMIT 5")


@pytest.mark.skip(reason="TODO(M3): requires the Docker Compose database (make up)")
def test_passenger_lookup_against_live_database() -> None:
    """get_passenger and search_passengers run against the real table via gateway_reader."""
