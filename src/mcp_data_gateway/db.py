"""Database access layer.

Owns every connection to PostgreSQL. Sessions are forced read-only and given a
statement timeout regardless of what the caller asks for (defense in depth,
see SECURITY.md).
"""

from mcp_data_gateway.config import Settings

# TODO(M2): implement with psycopg 3:
#   - connect using settings.database_url
#   - SET default_transaction_read_only = on
#   - SET statement_timeout = settings.statement_timeout_ms
#   - run every query through security.readonly_sql.assert_readonly() first
#   - always use parameterized queries; cap results at settings.max_rows


def execute_readonly(settings: Settings, sql: str, params: tuple = ()) -> list[dict]:
    """Execute a validated read-only query and return rows as dicts.

    Raises ``ReadOnlyViolation`` if ``sql`` fails the read-only guard.
    """
    raise NotImplementedError("TODO(M2): database layer not implemented yet")
