"""MCP server entrypoint.

Runs on stdio (ADR-0003) and exposes the read-only tools from
``mcp_data_gateway.tools``.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp-data-gateway")

# TODO(M3): register tools from tools/schema.py, tools/passengers.py, tools/stats.py.
# TODO(M3): initialize the database connection lazily on first tool call, so the
#   server starts even before PostgreSQL is up.


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
