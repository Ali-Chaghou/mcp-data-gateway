"""Read-only SQL guard.

Validates that a SQL string is a single read-only statement before it may reach
the database driver. Deny by default: anything not positively identified as a
plain ``SELECT`` is rejected.

This module is developed test-first — ``tests/test_readonly_sql.py`` is the
authoritative specification.
"""


class ReadOnlyViolation(Exception):
    """Raised when SQL fails the read-only check."""


def assert_readonly(sql: str) -> None:
    """Raise :class:`ReadOnlyViolation` unless ``sql`` is a single SELECT statement.

    TODO(M2): implement, rejecting at minimum:
      - anything whose first keyword is not SELECT (or WITH ... SELECT)
      - multiple statements / statement chaining via ';'
      - data-modifying keywords anywhere outside string literals
        (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, COPY, ...)
      - data-modifying CTEs (WITH x AS (DELETE ...))
      - empty or non-string input
    """
    raise NotImplementedError("TODO(M2): read-only guard not implemented yet")
