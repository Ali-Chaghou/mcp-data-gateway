"""Aggregate statistics tools over the Titanic demo dataset.

Only the ``passengers`` table is queried, and grouped statistics use a fixed,
fully-formed SQL template selected by an allow-listed ``group_by`` key — the
caller's value is never spliced into SQL. The grouped column is aliased
``group_value`` (an unquoted identifier the SQL guard accepts) and renamed to
``group`` when the result is shaped.
"""

from typing import Any

from mcp_data_gateway.config import Settings
from mcp_data_gateway.db import execute_readonly

Row = dict[str, Any]


class InvalidGroupByError(ValueError):
    """Raised when ``group_by`` is not an allow-listed column."""


_SUMMARY_SQL = "SELECT count(*) AS total_count, sum(survived) AS survived_count FROM passengers"

# One fixed template per allowed group_by. There is no string interpolation:
# survival_by only ever selects one of these constants by key.
_GROUP_BY_SQL: dict[str, str] = {
    "pclass": (
        "SELECT pclass AS group_value, count(*) AS total_count, "
        "sum(survived) AS survived_count FROM passengers GROUP BY pclass ORDER BY pclass"
    ),
    "sex": (
        "SELECT sex AS group_value, count(*) AS total_count, "
        "sum(survived) AS survived_count FROM passengers GROUP BY sex ORDER BY sex"
    ),
    "embarked": (
        "SELECT embarked AS group_value, count(*) AS total_count, "
        "sum(survived) AS survived_count FROM passengers GROUP BY embarked ORDER BY embarked"
    ),
}

ALLOWED_GROUP_BY: tuple[str, ...] = tuple(_GROUP_BY_SQL)


def _rate(survived: int, total: int) -> float:
    return round(survived / total, 4) if total else 0.0


def _counts(row: Row) -> tuple[int, int]:
    total = int(row.get("total_count") or 0)
    survived = int(row.get("survived_count") or 0)
    return total, survived


def survival_summary(settings: Settings, *, conn: Any = None) -> dict[str, Any]:
    """Return overall counts and survival rate across all passengers."""
    rows = execute_readonly(settings, _SUMMARY_SQL, conn=conn)
    total, survived = _counts(rows[0]) if rows else (0, 0)
    return {
        "total_count": total,
        "survived_count": survived,
        "survival_rate": _rate(survived, total),
    }


def survival_by(settings: Settings, group_by: str, *, conn: Any = None) -> list[Row]:
    """Return counts and survival rate for each value of an allow-listed column.

    ``group_by`` must be one of ``ALLOWED_GROUP_BY`` (``pclass``, ``sex``,
    ``embarked``); anything else raises :class:`InvalidGroupByError` before any
    SQL is issued.
    """
    if group_by not in _GROUP_BY_SQL:
        allowed = ", ".join(ALLOWED_GROUP_BY)
        raise InvalidGroupByError(f"group_by must be one of {allowed}, got {group_by!r}")

    rows = execute_readonly(settings, _GROUP_BY_SQL[group_by], conn=conn)
    result: list[Row] = []
    for row in rows:
        total, survived = _counts(row)
        result.append(
            {
                "group": row.get("group_value"),
                "total_count": total,
                "survived_count": survived,
                "survival_rate": _rate(survived, total),
            }
        )
    return result
