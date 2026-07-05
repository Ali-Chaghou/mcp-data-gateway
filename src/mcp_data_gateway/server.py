"""MCP server entrypoint.

Runs on stdio (ADR-0003) and exposes the read-only tools from
``mcp_data_gateway.tools`` through FastMCP. Each tool here is a thin wrapper that
forwards to a tool module; every wrapper goes through ``db.execute_readonly`` (by
way of those modules) and validates its arguments in code. There is no tool that
runs arbitrary SQL, and no argument names a table or column freely.

Settings are loaded lazily on first use, so importing this module never reads
the environment or opens a database connection.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_data_gateway.audit import audited, configure_logging
from mcp_data_gateway.config import Settings, load_settings
from mcp_data_gateway.serialization import json_safe
from mcp_data_gateway.tools import passengers, schema, stats

mcp = FastMCP("mcp-data-gateway")

_settings: Settings | None = None


def _get_settings() -> Settings:
    """Return the process settings, loading and caching them on first use."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


@mcp.tool()
def list_tables() -> list[str]:
    """List the tables the gateway can query."""
    return audited("list_tables", {}, lambda: json_safe(schema.list_tables()))


@mcp.tool()
def describe_table(table: str = "passengers") -> dict[str, Any]:
    """Describe the columns of an allow-listed table."""
    return audited(
        "describe_table",
        {"table": table},
        lambda: json_safe(schema.describe_table(_get_settings(), table)),
    )


@mcp.tool()
def get_passenger(passenger_id: int) -> dict[str, Any] | None:
    """Look up a single passenger by id; returns null if none exists."""
    return audited(
        "get_passenger",
        {"passenger_id": passenger_id},
        lambda: json_safe(passengers.get_passenger(_get_settings(), passenger_id)),
    )


@mcp.tool()
def search_passengers(
    pclass: int | None = None,
    survived: int | None = None,
    sex: str | None = None,
    embarked: str | None = None,
    min_age: float | None = None,
    max_age: float | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Search passengers by allow-listed filters (all optional)."""
    filters: dict[str, Any] = {
        "pclass": pclass,
        "survived": survived,
        "sex": sex,
        "embarked": embarked,
        "min_age": min_age,
        "max_age": max_age,
        "limit": limit,
    }
    return audited(
        "search_passengers",
        filters,
        lambda: json_safe(passengers.search_passengers(_get_settings(), **filters)),
    )


@mcp.tool()
def survival_summary() -> dict[str, Any]:
    """Overall passenger count and survival rate."""
    return audited(
        "survival_summary", {}, lambda: json_safe(stats.survival_summary(_get_settings()))
    )


@mcp.tool()
def survival_by(group_by: str) -> list[dict[str, Any]]:
    """Survival counts and rate grouped by an allow-listed column."""
    return audited(
        "survival_by",
        {"group_by": group_by},
        lambda: json_safe(stats.survival_by(_get_settings(), group_by)),
    )


def main() -> None:
    """Run the MCP server over stdio."""
    settings = _get_settings()  # validate configuration before serving
    configure_logging(settings)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
