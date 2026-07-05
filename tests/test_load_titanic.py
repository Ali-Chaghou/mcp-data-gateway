"""Tests for the Titanic loader script.

Unit tests cover the pure helpers (sample data, connection-string parsing,
admin settings) with no database. The DB setup itself is exercised by a skipped
integration test that needs the Docker Compose PostgreSQL instance (`make up`).
"""

import psycopg
import pytest

import load_titanic as loader
from integration_utils import requires_integration
from mcp_data_gateway.config import load_settings


def test_sample_data_is_well_formed() -> None:
    rows = loader.SAMPLE_PASSENGERS
    assert rows, "sample dataset must not be empty"
    ids = [row[0] for row in rows]
    assert len(ids) == len(set(ids)), "passenger_id must be unique"
    assert all(len(row) == len(loader.PASSENGER_COLUMNS) for row in rows)


def test_runtime_role_parsed_from_database_url() -> None:
    role, password = loader.runtime_role(
        "postgresql://gateway_reader:gateway_reader_dev_password@localhost:5432/agentdata"
    )
    assert role == "gateway_reader"
    assert password == "gateway_reader_dev_password"


def test_runtime_role_requires_password() -> None:
    with pytest.raises(SystemExit):
        loader.runtime_role("postgresql://gateway_reader@localhost:5432/agentdata")


def test_runtime_role_requires_database_url() -> None:
    with pytest.raises(SystemExit):
        loader.runtime_role(None)


def test_admin_conninfo_reads_postgres_env() -> None:
    info = loader.admin_conninfo(
        {
            "POSTGRES_DB": "agentdata",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "postgres",
            "POSTGRES_PORT": "5433",
        }
    )
    assert info["dbname"] == "agentdata"
    assert info["user"] == "postgres"
    assert info["port"] == "5433"
    assert info["host"] == "localhost"  # default when POSTGRES_HOST unset


def test_admin_conninfo_rejects_missing_settings() -> None:
    with pytest.raises(SystemExit):
        loader.admin_conninfo({"POSTGRES_USER": "postgres"})


@requires_integration
def test_loader_creates_select_only_role() -> None:
    """gateway_reader can SELECT passengers but has no write privilege.

    Uses a *raw* connection (no read-only session hardening) so the write is
    refused by the role's grants themselves — insufficient privilege — proving
    layer 3 independently of the session settings applied in db.connect.
    """
    settings = load_settings()
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM passengers")
            row = cur.fetchone()
            assert row is not None and row[0] == len(loader.SAMPLE_PASSENGERS)
        with conn.cursor() as cur, pytest.raises(psycopg.errors.InsufficientPrivilege):
            cur.execute(
                "INSERT INTO passengers "
                "(passenger_id, survived, pclass, name, sex, sibsp, parch) "
                "VALUES (999902, 0, 3, 'grant probe', 'male', 0, 0)"
            )
