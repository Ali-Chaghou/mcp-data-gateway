"""Database access layer.

Owns every connection to PostgreSQL. Sessions are forced read-only and given a
statement timeout regardless of what the caller asks for, and every statement is
checked by the read-only SQL guard before it runs (defense in depth, see
SECURITY.md). The database role remains the authoritative control; this layer is
what wires the gateway to it safely.
"""

from typing import Any

import psycopg
from psycopg.rows import dict_row

from mcp_data_gateway.config import Settings
from mcp_data_gateway.security.readonly_sql import apply_row_limit, assert_readonly

Row = dict[str, Any]


def _configure_session(conn: psycopg.Connection, settings: Settings) -> None:
    """Force the session read-only and apply the statement timeout.

    Runs as our own trusted setup, not agent input, so it does not pass through
    the SQL guard. ``set_config`` is used with a bound parameter so the timeout
    value is never interpolated into SQL text.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('default_transaction_read_only', 'on', false)")
        cur.execute(
            "SELECT set_config('statement_timeout', %s, false)",
            (str(settings.statement_timeout_ms),),
        )


def connect(settings: Settings) -> psycopg.Connection:
    """Open a configured, read-only connection to PostgreSQL."""
    conn = psycopg.connect(settings.database_url, autocommit=True)
    try:
        _configure_session(conn, settings)
    except Exception:
        conn.close()
        raise
    return conn


def _fetch(conn: psycopg.Connection, sql: str, params: tuple[Any, ...]) -> list[Row]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def execute_readonly(
    settings: Settings,
    sql: str,
    params: tuple[Any, ...] = (),
    *,
    conn: psycopg.Connection | None = None,
) -> list[Row]:
    """Execute a validated read-only query and return rows as dicts.

    The statement is checked by :func:`assert_readonly` *before* it reaches the
    database, then capped to ``settings.max_rows`` by :func:`apply_row_limit`.
    ``params`` are always bound separately — user input is never interpolated
    into the SQL text. Pass ``conn`` to reuse an existing connection; otherwise
    a fresh configured connection is opened and closed.

    Raises :class:`ReadOnlyViolation` if ``sql`` fails the read-only guard.
    """
    assert_readonly(sql)
    limited = apply_row_limit(sql, settings.max_rows)

    if conn is not None:
        return _fetch(conn, limited, params)
    with connect(settings) as conn:
        return _fetch(conn, limited, params)
