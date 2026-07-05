"""Tests for JSON-safe serialization of tool results."""

import json
from decimal import Decimal

from mcp_data_gateway.serialization import json_safe


def test_decimal_becomes_float() -> None:
    result = json_safe(Decimal("7.25"))
    assert result == 7.25
    assert isinstance(result, float)


def test_json_native_values_pass_through() -> None:
    for value in ["x", 3, True, None, 1.5]:
        assert json_safe(value) is value


def test_nested_dict_and_list_are_converted() -> None:
    value = {
        "fare": Decimal("7.25"),
        "nested": {"age": Decimal("22")},
        "history": [Decimal("1.5"), {"rate": Decimal("0.4")}],
    }
    assert json_safe(value) == {
        "fare": 7.25,
        "nested": {"age": 22.0},
        "history": [1.5, {"rate": 0.4}],
    }


def test_tuple_becomes_list() -> None:
    assert json_safe((Decimal("1"), "a")) == [1.0, "a"]


def test_passenger_style_row_is_json_serializable() -> None:
    row = {
        "passenger_id": 1,
        "name": "Braund, Mr. Owen Harris",
        "age": Decimal("22"),
        "fare": Decimal("7.25"),
        "embarked": None,
    }
    safe = json_safe(row)
    # The whole thing round-trips through json without error.
    assert json.loads(json.dumps(safe)) == {
        "passenger_id": 1,
        "name": "Braund, Mr. Owen Harris",
        "age": 22.0,
        "fare": 7.25,
        "embarked": None,
    }


def test_source_is_not_mutated() -> None:
    row = {"age": Decimal("22"), "tags": [Decimal("1")]}
    json_safe(row)
    assert row["age"] == Decimal("22")
    assert isinstance(row["age"], Decimal)
    assert isinstance(row["tags"][0], Decimal)
