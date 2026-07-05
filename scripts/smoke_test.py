"""End-to-end smoke test for local development.

Loads settings, connects with the runtime ``DATABASE_URL``, calls each tool the
way the MCP server does, and checks the results are sane. It also verifies write
protection by attempting an INSERT straight through psycopg (bypassing the guard)
so it exercises the database role/session itself.

Expected local-setup problems (missing config, database not up) exit with a
short instructional message rather than a stack trace.

Usage:
    python scripts/smoke_test.py     # or: make smoke
"""

import sys

import psycopg

from mcp_data_gateway.config import ConfigError, Settings, load_settings
from mcp_data_gateway.db import connect
from mcp_data_gateway.tools.passengers import get_passenger, search_passengers
from mcp_data_gateway.tools.schema import describe_table, list_tables
from mcp_data_gateway.tools.stats import survival_by, survival_summary

# A fully-valid row so the only reason an INSERT can fail is the read-only role
# or session — not a constraint violation. The id is far outside the sample data.
_PROBE_INSERT = (
    "INSERT INTO passengers (passenger_id, survived, pclass, name, sex, sibsp, parch) "
    "VALUES (999999, 0, 3, 'smoke-test probe', 'male', 0, 0)"
)


def _short(exc: BaseException) -> str:
    """Return the first line of an exception message, or its type name."""
    text = str(exc).strip()
    return text.splitlines()[0] if text else exc.__class__.__name__


def setup_message(reason: str) -> str:
    """A friendly, actionable message for expected local-setup failures."""
    return (
        f"Smoke test could not run: {reason}\n\n"
        "This usually means local setup isn't ready yet. Try:\n"
        "  cp .env.example .env\n"
        "  make up\n"
        "  make load-data\n"
        "then re-run: make smoke"
    )


# --- Individual checks (each raises AssertionError on failure) -------------
#
# Checks use an explicit ``_require`` rather than ``assert`` so they still run
# under ``python -O`` (which strips assert statements).


def _require(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_list_tables(settings: Settings, conn: psycopg.Connection) -> None:
    tables = list_tables()
    _require("passengers" in tables, f"'passengers' not in {tables}")


def check_describe_table(settings: Settings, conn: psycopg.Connection) -> None:
    meta = describe_table(settings, "passengers", conn=conn)
    names = [col["name"] for col in meta["columns"]]
    _require({"passenger_id", "survived", "sex"} <= set(names), f"unexpected columns: {names}")


def check_get_passenger(settings: Settings, conn: psycopg.Connection) -> None:
    row = get_passenger(settings, 1, conn=conn)
    _require(row is not None, "passenger 1 not found — did you run 'make load-data'?")


def check_search_passengers(settings: Settings, conn: psycopg.Connection) -> None:
    rows = search_passengers(settings, sex="female", conn=conn)
    _require(isinstance(rows, list), f"expected a list, got {type(rows).__name__}")


def check_survival_summary(settings: Settings, conn: psycopg.Connection) -> None:
    summary = survival_summary(settings, conn=conn)
    missing = {"total_count", "survived_count", "survival_rate"} - summary.keys()
    _require(not missing, f"summary missing keys: {missing}")


def check_survival_by(settings: Settings, conn: psycopg.Connection) -> None:
    groups = survival_by(settings, "sex", conn=conn)
    _require(bool(groups), "survival_by('sex') returned no rows")
    _require("group" in groups[0], f"grouped row missing 'group': {groups[0]}")


def check_write_protection(settings: Settings, conn: psycopg.Connection) -> None:
    """A direct INSERT (not via the guard) must be refused by the database."""
    try:
        with conn.cursor() as cur:
            cur.execute(_PROBE_INSERT)
    except psycopg.Error:
        return  # good: the runtime role/session refused the write
    raise AssertionError("INSERT succeeded — the runtime role is NOT read-only")


CHECKS = [
    ("passengers is listed", check_list_tables),
    ("describe_table returns passenger columns", check_describe_table),
    ("get_passenger(1) returns a row", check_get_passenger),
    ("search_passengers returns a list", check_search_passengers),
    ("survival_summary has the expected fields", check_survival_summary),
    ("survival_by('sex') returns grouped rows", check_survival_by),
    ("direct writes are refused by the database", check_write_protection),
]


def run_checks(settings: Settings, conn: psycopg.Connection) -> list[str]:
    """Run every check, printing progress, and return the names that failed."""
    failures: list[str] = []
    for name, check in CHECKS:
        try:
            check(settings, conn)
        except AssertionError as exc:
            print(f"  FAIL  {name}: {exc}")
            failures.append(name)
        except Exception as exc:  # report, don't let one failure crash the run
            print(f"  FAIL  {name}: unexpected error: {_short(exc)}")
            failures.append(name)
        else:
            print(f"  ok    {name}")
    return failures


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(setup_message(f"configuration error: {exc}"))
        return 1

    try:
        conn = connect(settings)
    except psycopg.OperationalError as exc:
        print(setup_message(f"could not connect to PostgreSQL ({_short(exc)})"))
        return 1

    print("Running smoke checks against the runtime connection:\n")
    try:
        failures = run_checks(settings, conn)
    finally:
        conn.close()

    if failures:
        print(f"\n{len(failures)} of {len(CHECKS)} checks failed.")
        return 1
    print(f"\nAll {len(CHECKS)} smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
