"""Passenger lookup tools over the Titanic demo dataset.

Every query targets only the ``passengers`` table, is built from column names
that are string literals in this module (never caller input), and passes all
caller-supplied values as bound parameters. Filters are validated against
explicit allow-lists *before* any SQL is issued.
"""

from dataclasses import replace
from typing import Any

from mcp_data_gateway.config import Settings
from mcp_data_gateway.db import execute_readonly

Row = dict[str, Any]


class InvalidFilterError(ValueError):
    """Raised when a lookup argument fails validation."""


def _is_int(value: object) -> bool:
    # bool is a subclass of int; exclude it so True/False are not accepted as ints.
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _validate_passenger_id(passenger_id: object) -> None:
    if not _is_int(passenger_id) or passenger_id < 1:
        raise InvalidFilterError(f"passenger_id must be a positive integer, got {passenger_id!r}")


def _validate_limit(limit: object, max_rows: int) -> int:
    if limit is None:
        return max_rows
    if not _is_int(limit) or limit < 1:
        raise InvalidFilterError(f"limit must be a positive integer, got {limit!r}")
    if limit > max_rows:
        raise InvalidFilterError(f"limit {limit} exceeds the maximum of {max_rows}")
    return limit


def get_passenger(settings: Settings, passenger_id: int, *, conn: Any = None) -> Row | None:
    """Return one passenger by id, or ``None`` if no such passenger exists."""
    _validate_passenger_id(passenger_id)
    rows = execute_readonly(
        settings,
        "SELECT * FROM passengers WHERE passenger_id = %s LIMIT 1",
        (passenger_id,),
        conn=conn,
    )
    return rows[0] if rows else None


def search_passengers(
    settings: Settings,
    *,
    pclass: int | None = None,
    survived: int | bool | None = None,
    sex: str | None = None,
    embarked: str | None = None,
    min_age: float | None = None,
    max_age: float | None = None,
    limit: int | None = None,
    conn: Any = None,
) -> list[Row]:
    """Return passengers matching the given allow-listed filters.

    Each filter is optional; validated values are compared with bound
    parameters against fixed columns. Results are ordered by ``passenger_id``
    and capped at ``limit`` (default and hard ceiling: ``settings.max_rows``).
    """
    clauses: list[str] = []
    params: list[Any] = []

    if pclass is not None:
        if not _is_int(pclass) or pclass not in (1, 2, 3):
            raise InvalidFilterError(f"pclass must be 1, 2, or 3, got {pclass!r}")
        clauses.append("pclass = %s")
        params.append(pclass)

    if survived is not None:
        if isinstance(survived, bool):
            survived = int(survived)
        if not _is_int(survived) or survived not in (0, 1):
            raise InvalidFilterError(f"survived must be 0 or 1, got {survived!r}")
        clauses.append("survived = %s")
        params.append(survived)

    if sex is not None:
        if sex not in ("male", "female"):
            raise InvalidFilterError(f"sex must be 'male' or 'female', got {sex!r}")
        clauses.append("sex = %s")
        params.append(sex)

    if embarked is not None:
        if embarked not in ("C", "Q", "S"):
            raise InvalidFilterError(f"embarked must be 'C', 'Q', or 'S', got {embarked!r}")
        clauses.append("embarked = %s")
        params.append(embarked)

    if min_age is not None:
        if not _is_number(min_age) or min_age < 0:
            raise InvalidFilterError(f"min_age must be a non-negative number, got {min_age!r}")
        clauses.append("age >= %s")
        params.append(min_age)

    if max_age is not None:
        if not _is_number(max_age) or max_age < 0:
            raise InvalidFilterError(f"max_age must be a non-negative number, got {max_age!r}")
        clauses.append("age <= %s")
        params.append(max_age)

    if min_age is not None and max_age is not None and max_age < min_age:
        raise InvalidFilterError(f"max_age {max_age} must not be smaller than min_age {min_age}")

    effective_limit = _validate_limit(limit, settings.max_rows)

    query = "SELECT * FROM passengers"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY passenger_id"

    # Honor the caller's limit through the existing row-limit mechanism rather
    # than embedding a value in the SQL text.
    capped = replace(settings, max_rows=effective_limit)
    return execute_readonly(capped, query, tuple(params), conn=conn)
