"""Specification for the read-only SQL guard.

This suite is the authoritative definition of what SQL the gateway may execute.
Anything not in ALLOWED shape must raise ReadOnlyViolation — deny by default.
"""

import pytest

from mcp_data_gateway.security.readonly_sql import (
    ReadOnlyViolation,
    apply_row_limit,
    assert_readonly,
)

ALLOWED = [
    "SELECT 1",
    "SELECT 1;",  # a single trailing semicolon is harmless
    "select name, age from passengers where pclass = %s",
    "SELECT count(*) FROM passengers GROUP BY sex",
    "SELECT * FROM public.passengers ORDER BY age DESC LIMIT 10",
    "SELECT name FROM passengers WHERE name = 'O''Brien; DROP'",  # metachars inside a literal
    "SELECT * FROM passengers p",  # table alias must still pass
    "SELECT p.name FROM passengers AS p WHERE p.pclass = %s",  # aliased column refs
    "SELECT max(fare) FROM passengers WHERE embarked IN ('C', 'S')",  # func + IN list commas
]

REJECTED = [
    "",
    "   ",
    "INSERT INTO passengers VALUES (1)",
    "UPDATE passengers SET survived = 1",
    "DELETE FROM passengers",
    "DROP TABLE passengers",
    "ALTER TABLE passengers ADD COLUMN backdoor int",
    "CREATE TABLE evil (id int)",
    "TRUNCATE passengers",
    "GRANT ALL ON passengers TO public",
    "REVOKE ALL ON passengers FROM public",
    "COPY passengers TO '/tmp/out.csv'",
    "CALL some_procedure()",
    "EXECUTE prepared_stmt",
    "SELECT 1; DELETE FROM passengers",  # statement chaining
    "SELECT 1;;",  # only one trailing semicolon is tolerated
    "SELECT pg_sleep(10)",  # connection stalling
    "SELECT * FROM dblink('host=evil', 'SELECT 1') AS t(x int)",  # cross-database access
    "SELECT dblink_exec('host=evil', 'DELETE FROM passengers')",
    "SELECT lo_import('/etc/passwd')",  # server filesystem read
    "SELECT lo_export(123, '/tmp/out')",  # server filesystem write
    "WITH x AS (DELETE FROM passengers RETURNING *) SELECT * FROM x",  # writing CTE
    "SELECT * FROM passengers -- ; DROP TABLE passengers",  # comment can hide code
    "SELECT * /* sneaky */ FROM passengers",
    "SELECT * FROM crew",  # table not on the allow-list
    "SELECT * FROM pg_catalog.pg_tables",  # catalog snooping
    # comma joins to unauthorized tables (the allow-list must see every relation)
    "SELECT * FROM passengers, users",
    "SELECT u.* FROM passengers p, users u",
    "SELECT * FROM passengers, users, secrets",
    "SELECT * FROM passengers, pg_catalog.pg_tables",
    # explicit joins of every flavor to unauthorized tables
    "SELECT * FROM passengers JOIN pg_catalog.pg_tables ON true",
    "SELECT * FROM passengers CROSS JOIN users",
    "SELECT * FROM passengers LEFT JOIN secrets ON true",
    "SELECT * FROM passengers JOIN LATERAL users ON true",
    "SELECT * FROM (SELECT 1) s, users",  # comma join after a subquery term
    # dangerous built-in functions
    "SELECT pg_read_file('/app/.env')",
    "SELECT pg_ls_dir('/')",
    "SELECT pg_stat_file('/etc/passwd')",
    "SELECT current_setting('data_directory')",
    "SELECT set_config('search_path', 'evil', false)",
    "SELECT query_to_xml('SELECT * FROM users', true, true, '')",
    "SELECT query_to_xml_and_xmlschema('SELECT * FROM users', true, true, '')",
    'SELECT * FROM "passengers"',  # quoted identifiers bypass name checks
    "SELECT * INTO copied FROM passengers",  # SELECT INTO creates a table
    "EXPLAIN ANALYZE SELECT * FROM passengers",  # ANALYZE executes the query
    "SET search_path TO evil",
    "SELECT * FROM passengers FOR UPDATE",  # row locks are not read-only
    "BEGIN",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_allows_plain_selects(sql: str) -> None:
    assert_readonly(sql)  # must not raise


@pytest.mark.parametrize("sql", REJECTED)
def test_rejects_non_readonly_sql(sql: str) -> None:
    with pytest.raises(ReadOnlyViolation):
        assert_readonly(sql)


@pytest.mark.parametrize("sql", [None, 42, ["SELECT 1"]])
def test_rejects_non_string_input(sql: object) -> None:
    with pytest.raises(ReadOnlyViolation):
        assert_readonly(sql)  # type: ignore[arg-type]


def test_row_limit_added_when_missing() -> None:
    result = apply_row_limit("SELECT * FROM passengers", 200)
    assert result == "SELECT * FROM passengers LIMIT 200"


def test_row_limit_kept_when_within_cap() -> None:
    sql = "SELECT * FROM passengers LIMIT 10"
    assert apply_row_limit(sql, 200) == sql


def test_row_limit_clamped_to_cap() -> None:
    result = apply_row_limit("SELECT * FROM passengers LIMIT 5000", 200)
    assert result == "SELECT * FROM passengers LIMIT 200"


def test_row_limit_clamp_preserves_offset() -> None:
    result = apply_row_limit("SELECT * FROM passengers LIMIT 500 OFFSET 20", 100)
    assert result == "SELECT * FROM passengers LIMIT 100 OFFSET 20"


def test_row_limit_requires_positive_cap() -> None:
    with pytest.raises(ValueError):
        apply_row_limit("SELECT 1", 0)
