"""Specification for the read-only SQL guard.

This suite is the authoritative definition of what SQL the gateway may execute.
It is written ahead of the implementation (M2); cases marked xfail describe
required behavior that does not pass yet.
"""

import pytest

from mcp_data_gateway.security.readonly_sql import ReadOnlyViolation, assert_readonly

ALLOWED = [
    "SELECT 1",
    "select name, age from passengers where pclass = %s",
    "SELECT count(*) FROM passengers GROUP BY sex",
]

REJECTED = [
    "INSERT INTO passengers VALUES (1)",
    "UPDATE passengers SET survived = 1",
    "DELETE FROM passengers",
    "DROP TABLE passengers",
    "TRUNCATE passengers",
    "GRANT ALL ON passengers TO public",
    "SELECT 1; DELETE FROM passengers",  # statement chaining
    "WITH x AS (DELETE FROM passengers RETURNING *) SELECT * FROM x",  # writing CTE
    "",
]


@pytest.mark.parametrize("sql", ALLOWED)
@pytest.mark.xfail(reason="TODO(M2): guard not implemented yet", strict=True)
def test_allows_plain_selects(sql: str) -> None:
    assert_readonly(sql)  # must not raise


@pytest.mark.parametrize("sql", REJECTED)
def test_rejects_non_readonly_sql(sql: str) -> None:
    with pytest.raises((ReadOnlyViolation, NotImplementedError)):
        assert_readonly(sql)
