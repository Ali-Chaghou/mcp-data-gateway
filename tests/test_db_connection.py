"""Tests for the database layer (db.py).

Integration tests here require the Docker Compose PostgreSQL instance
(`make up`); they are skipped when the database is unreachable.
"""

import pytest

# TODO(M2): implement alongside db.py:
#   - connects using settings.database_url
#   - session has default_transaction_read_only = on
#   - statement_timeout is applied
#   - an INSERT attempted at the driver level is refused by the database
#   - results are capped at settings.max_rows


@pytest.mark.skip(reason="TODO(M2): database layer not implemented yet")
def test_connection_is_read_only() -> None:
    """The database session must refuse writes even at the driver level."""
