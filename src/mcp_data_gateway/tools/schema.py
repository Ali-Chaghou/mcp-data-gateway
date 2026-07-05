"""Schema introspection tools.

Lets an agent discover what data exists before querying it, without ever
exposing arbitrary database metadata. The column descriptions are curated in
code (they mirror the schema created by ``scripts/load_titanic.py``), and the
only live database access is a guarded reachability probe routed through
``db.execute_readonly`` — so the allow-list boundary is enforced the same way as
for any other query.
"""

from typing import Any

from mcp_data_gateway.config import Settings
from mcp_data_gateway.db import execute_readonly
from mcp_data_gateway.security.readonly_sql import ALLOWED_TABLES

Column = dict[str, Any]


class UnknownTableError(ValueError):
    """Raised when a table is not on the gateway's allow-list."""


# Curated column metadata for each allow-listed table. This is the authoritative
# description the tool exposes; it is intentionally hand-maintained alongside the
# loader's ``CREATE TABLE`` rather than read from ``information_schema``, which
# the SQL guard (correctly) refuses to query.
_TABLE_COLUMNS: dict[str, list[Column]] = {
    "passengers": [
        {
            "name": "passenger_id",
            "type": "integer",
            "nullable": False,
            "description": "Unique passenger identifier.",
        },
        {
            "name": "survived",
            "type": "smallint",
            "nullable": False,
            "description": "1 if the passenger survived, 0 otherwise.",
        },
        {
            "name": "pclass",
            "type": "smallint",
            "nullable": False,
            "description": "Ticket class: 1 = first, 2 = second, 3 = third.",
        },
        {"name": "name", "type": "text", "nullable": False, "description": "Passenger name."},
        {"name": "sex", "type": "text", "nullable": False, "description": "Passenger sex."},
        {
            "name": "age",
            "type": "numeric",
            "nullable": True,
            "description": "Age in years; null if unknown.",
        },
        {
            "name": "sibsp",
            "type": "smallint",
            "nullable": False,
            "description": "Number of siblings and spouses aboard.",
        },
        {
            "name": "parch",
            "type": "smallint",
            "nullable": False,
            "description": "Number of parents and children aboard.",
        },
        {
            "name": "fare",
            "type": "numeric",
            "nullable": True,
            "description": "Fare paid; null if unknown.",
        },
        {
            "name": "embarked",
            "type": "text",
            "nullable": True,
            "description": "Port of embarkation: C, Q, or S; null if unknown.",
        },
    ],
}

# A constant, allow-listed probe per table — never built from caller input.
_PROBE_SQL: dict[str, str] = {
    "passengers": "SELECT 1 FROM passengers LIMIT 1",
}


def list_tables() -> list[str]:
    """Return the names of tables the gateway will query, sorted."""
    return sorted(ALLOWED_TABLES)


def _require_allowed(table: str) -> None:
    if table not in ALLOWED_TABLES:
        allowed = ", ".join(sorted(ALLOWED_TABLES))
        raise UnknownTableError(f"table {table!r} is not available; allowed tables: {allowed}")


def describe_table(
    settings: Settings,
    table: str = "passengers",
    *,
    conn: Any = None,
) -> dict[str, Any]:
    """Return column metadata for an allow-listed ``table``.

    Validates ``table`` against the allow-list first, then confirms the table is
    reachable via a guarded read through :func:`db.execute_readonly` before
    returning the curated column descriptions. Raises :class:`UnknownTableError`
    for anything outside the allow-list — no SQL is issued in that case.
    """
    _require_allowed(table)
    execute_readonly(settings, _PROBE_SQL[table], conn=conn)
    return {"table": table, "columns": [dict(column) for column in _TABLE_COLUMNS[table]]}
