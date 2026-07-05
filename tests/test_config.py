"""Tests for environment-based configuration loading and validation.

``load_settings`` accepts an explicit mapping so these tests stay isolated from
the real process environment.
"""

import pytest

from mcp_data_gateway.config import (
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_ROWS,
    DEFAULT_STATEMENT_TIMEOUT_MS,
    MAX_ROWS_LIMIT,
    STATEMENT_TIMEOUT_MS_LIMIT,
    ConfigError,
    Settings,
    load_settings,
)

DB_URL = "postgresql://user:pw@localhost:5432/agentdata"


def test_valid_config_all_values() -> None:
    settings = load_settings(
        {
            "DATABASE_URL": DB_URL,
            "MAX_ROWS": "500",
            "STATEMENT_TIMEOUT_MS": "3000",
            "LOG_LEVEL": "DEBUG",
        }
    )
    assert settings == Settings(
        database_url=DB_URL,
        max_rows=500,
        statement_timeout_ms=3000,
        log_level="DEBUG",
    )


def test_defaults_when_optional_values_absent() -> None:
    settings = load_settings({"DATABASE_URL": DB_URL})
    assert settings.max_rows == DEFAULT_MAX_ROWS
    assert settings.statement_timeout_ms == DEFAULT_STATEMENT_TIMEOUT_MS
    assert settings.log_level == DEFAULT_LOG_LEVEL


def test_log_level_is_case_insensitive() -> None:
    settings = load_settings({"DATABASE_URL": DB_URL, "LOG_LEVEL": "warning"})
    assert settings.log_level == "WARNING"


@pytest.mark.parametrize("env", [{}, {"DATABASE_URL": ""}, {"DATABASE_URL": "   "}])
def test_missing_database_url_is_rejected(env: dict[str, str]) -> None:
    with pytest.raises(ConfigError):
        load_settings(env)


@pytest.mark.parametrize(
    "value",
    ["0", "-1", "abc", "1.5", str(MAX_ROWS_LIMIT + 1)],
)
def test_invalid_max_rows_is_rejected(value: str) -> None:
    with pytest.raises(ConfigError):
        load_settings({"DATABASE_URL": DB_URL, "MAX_ROWS": value})


def test_blank_optional_value_falls_back_to_default() -> None:
    settings = load_settings({"DATABASE_URL": DB_URL, "MAX_ROWS": "  "})
    assert settings.max_rows == DEFAULT_MAX_ROWS


@pytest.mark.parametrize(
    "value",
    ["0", "-100", "notanumber", str(STATEMENT_TIMEOUT_MS_LIMIT + 1)],
)
def test_invalid_statement_timeout_is_rejected(value: str) -> None:
    with pytest.raises(ConfigError):
        load_settings({"DATABASE_URL": DB_URL, "STATEMENT_TIMEOUT_MS": value})


@pytest.mark.parametrize("value", ["TRACE", "verbose", "10", "warn"])
def test_invalid_log_level_is_rejected(value: str) -> None:
    with pytest.raises(ConfigError):
        load_settings({"DATABASE_URL": DB_URL, "LOG_LEVEL": value})


def test_bounds_are_inclusive() -> None:
    settings = load_settings(
        {
            "DATABASE_URL": DB_URL,
            "MAX_ROWS": str(MAX_ROWS_LIMIT),
            "STATEMENT_TIMEOUT_MS": str(STATEMENT_TIMEOUT_MS_LIMIT),
        }
    )
    assert settings.max_rows == MAX_ROWS_LIMIT
    assert settings.statement_timeout_ms == STATEMENT_TIMEOUT_MS_LIMIT
