"""Schema introspection tools.

Lets an agent discover what data exists before querying it.
"""

# TODO(M3): implement and register on the MCP server:
#   - list_tables() -> table names in the public schema (information_schema query)
#   - describe_table(table: str) -> columns, types, nullability
#     (table name validated against an allow-list, never interpolated)


def list_tables() -> list[str]:
    """Return the names of queryable tables."""
    raise NotImplementedError("TODO(M3)")


def describe_table(table: str) -> list[dict]:
    """Return column metadata for ``table``."""
    raise NotImplementedError("TODO(M3)")
