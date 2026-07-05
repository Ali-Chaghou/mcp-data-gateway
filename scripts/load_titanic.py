"""Load the Titanic demo dataset into PostgreSQL for local development.

Idempotent: safe to run repeatedly. It connects as the local **admin** user
(``POSTGRES_*`` env vars), creates the ``passengers`` table, loads a small,
deterministic sample dataset, and creates/updates the SELECT-only runtime role
the gateway connects as. The runtime role name and password are read from
``DATABASE_URL`` so they always match ``.env.example``.

Usage:
    python scripts/load_titanic.py
"""

import os
from collections.abc import Mapping
from urllib.parse import unquote, urlparse

import psycopg
from psycopg import sql

# --- Schema and deterministic sample data ---------------------------------

PASSENGER_COLUMNS: tuple[str, ...] = (
    "passenger_id",
    "survived",
    "pclass",
    "name",
    "sex",
    "age",
    "sibsp",
    "parch",
    "fare",
    "embarked",
)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS passengers (
    passenger_id integer PRIMARY KEY,
    survived     smallint NOT NULL,
    pclass       smallint NOT NULL,
    name         text     NOT NULL,
    sex          text     NOT NULL,
    age          numeric,
    sibsp        smallint NOT NULL,
    parch        smallint NOT NULL,
    fare         numeric,
    embarked     text
)
"""

INSERT_SQL = """
INSERT INTO passengers
    (passenger_id, survived, pclass, name, sex, age, sibsp, parch, fare, embarked)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

# A small, fixed, Titanic-style sample. Committed in code so `make load-data`
# needs no network access and produces identical data every run.
SAMPLE_PASSENGERS: list[tuple[object, ...]] = [
    (1, 0, 3, "Braund, Mr. Owen Harris", "male", 22, 1, 0, 7.25, "S"),
    (2, 1, 1, "Cumings, Mrs. John Bradley", "female", 38, 1, 0, 71.28, "C"),
    (3, 1, 3, "Heikkinen, Miss. Laina", "female", 26, 0, 0, 7.92, "S"),
    (4, 1, 1, "Futrelle, Mrs. Jacques Heath", "female", 35, 1, 0, 53.10, "S"),
    (5, 0, 3, "Allen, Mr. William Henry", "male", 35, 0, 0, 8.05, "S"),
    (6, 0, 3, "Moran, Mr. James", "male", None, 0, 0, 8.46, "Q"),
    (7, 0, 1, "McCarthy, Mr. Timothy J", "male", 54, 0, 0, 51.86, "S"),
    (8, 0, 3, "Palsson, Master. Gosta Leonard", "male", 2, 3, 1, 21.08, "S"),
    (9, 1, 3, "Johnson, Mrs. Oscar W", "female", 27, 0, 2, 11.13, "S"),
    (10, 1, 2, "Nasser, Mrs. Nicholas", "female", 14, 1, 0, 30.07, "C"),
    (11, 1, 3, "Sandstrom, Miss. Marguerite Rut", "female", 4, 1, 1, 16.70, "S"),
    (12, 1, 1, "Bonnell, Miss. Elizabeth", "female", 58, 0, 0, 26.55, "S"),
    (13, 0, 3, "Saundercock, Mr. William Henry", "male", 20, 0, 0, 8.05, "S"),
    (14, 0, 3, "Andersson, Mr. Anders Johan", "male", 39, 1, 5, 31.28, "S"),
    (15, 0, 3, "Vestrom, Miss. Hulda Amanda", "female", 14, 0, 0, 7.85, "S"),
]

RUNTIME_ROLE_FALLBACK = "gateway_reader"


# --- Pure helpers (unit-tested without a database) ------------------------


def runtime_role(database_url: str | None) -> tuple[str, str]:
    """Return the (role, password) the gateway will use, parsed from DATABASE_URL.

    Reading these from the connection string keeps the role created here in sync
    with what the server actually connects as, with no password duplicated in
    code.
    """
    if not database_url:
        raise SystemExit("DATABASE_URL must be set to create the runtime role")
    parsed = urlparse(database_url)
    role = parsed.username or RUNTIME_ROLE_FALLBACK
    if not parsed.password:
        raise SystemExit("DATABASE_URL must include the runtime role's password")
    return role, unquote(parsed.password)


def admin_conninfo(env: Mapping[str, str]) -> dict[str, str]:
    """Build admin connection parameters from the POSTGRES_* environment.

    Only used for setup — never as the gateway's runtime connection.
    """
    missing = [k for k in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD") if not env.get(k)]
    if missing:
        raise SystemExit(f"missing admin settings: {', '.join(missing)}")
    return {
        "host": env.get("POSTGRES_HOST", "localhost"),
        "port": env.get("POSTGRES_PORT", "5432"),
        "dbname": env["POSTGRES_DB"],
        "user": env["POSTGRES_USER"],
        "password": env["POSTGRES_PASSWORD"],
    }


# --- Database setup steps --------------------------------------------------


def create_schema(cur: psycopg.Cursor) -> None:
    cur.execute(CREATE_TABLE_SQL)


def load_sample_data(cur: psycopg.Cursor) -> None:
    """Replace all rows with the deterministic sample (idempotent reload)."""
    cur.execute("TRUNCATE passengers")
    cur.executemany(INSERT_SQL, SAMPLE_PASSENGERS)


def configure_runtime_role(cur: psycopg.Cursor, role: str, password: str, dbname: str) -> None:
    """Create/update ``role`` as a login role with SELECT-only on passengers.

    Identifiers and the password are composed with psycopg.sql (quoted, never
    string-interpolated). Re-running only resets the grants to the same state.
    """
    role_ident = sql.Identifier(role)
    db_ident = sql.Identifier(dbname)
    grant = sql.SQL(" WITH LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
        sql.Literal(password)
    )

    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
    if cur.fetchone() is None:
        cur.execute(sql.SQL("CREATE ROLE {}").format(role_ident) + grant)
    else:
        cur.execute(sql.SQL("ALTER ROLE {}").format(role_ident) + grant)

    # Deny by default at every level — database, schema, and table — for both
    # PUBLIC and the runtime role, then grant back exactly what a reader needs.
    cur.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(db_ident))
    cur.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM {}").format(db_ident, role_ident))
    cur.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
    cur.execute(sql.SQL("REVOKE ALL ON SCHEMA public FROM {}").format(role_ident))
    cur.execute("REVOKE ALL ON passengers FROM PUBLIC")
    cur.execute(sql.SQL("REVOKE ALL ON passengers FROM {}").format(role_ident))

    cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(db_ident, role_ident))
    cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role_ident))
    cur.execute(sql.SQL("GRANT SELECT ON passengers TO {}").format(role_ident))


def main() -> None:
    env = os.environ
    role, password = runtime_role(env.get("DATABASE_URL"))
    info = admin_conninfo(env)

    with psycopg.connect(autocommit=True, **info) as conn, conn.cursor() as cur:
        create_schema(cur)
        load_sample_data(cur)
        configure_runtime_role(cur, role, password, info["dbname"])
        cur.execute("SELECT count(*) FROM passengers")
        row = cur.fetchone()
        count = row[0] if row else 0

    print(f"Loaded {count} passengers; runtime role '{role}' has SELECT-only access.")


if __name__ == "__main__":
    main()
