"""Environment-based configuration.

All settings come from the environment (``.env`` in local development); nothing
sensitive lives in code. Values are validated when they are loaded, so the
process fails fast with a clear message instead of starting in a bad state or
discovering the problem on the first query.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

#: Upper bounds guard against pathological configuration — a result cap so large
#: it exhausts memory, or a statement timeout so long the server stops being
#: responsive. They are deliberately generous; normal use sits well below them.
MAX_ROWS_LIMIT: Final[int] = 10_000
STATEMENT_TIMEOUT_MS_LIMIT: Final[int] = 60_000

DEFAULT_MAX_ROWS: Final[int] = 200
DEFAULT_STATEMENT_TIMEOUT_MS: Final[int] = 5_000
DEFAULT_LOG_LEVEL: Final[str] = "INFO"

_LOG_LEVELS: Final[frozenset[str]] = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Validated runtime settings for the gateway."""

    database_url: str
    max_rows: int = DEFAULT_MAX_ROWS
    statement_timeout_ms: int = DEFAULT_STATEMENT_TIMEOUT_MS
    log_level: str = DEFAULT_LOG_LEVEL


def _required_str(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigError(f"{name} is required and must be a non-empty string")
    return value


def _bounded_int(env: Mapping[str, str], name: str, default: int, upper: int) -> int:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from None
    if value < 1:
        raise ConfigError(f"{name} must be a positive integer, got {value}")
    if value > upper:
        raise ConfigError(f"{name} must be at most {upper}, got {value}")
    return value


def _log_level(env: Mapping[str, str], name: str, default: str) -> str:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    value = raw.strip().upper()
    if value not in _LOG_LEVELS:
        allowed = ", ".join(sorted(_LOG_LEVELS))
        raise ConfigError(f"{name} must be one of {allowed}, got {raw!r}")
    return value


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Load and validate settings from ``env`` (defaults to ``os.environ``).

    Raises :class:`ConfigError` if ``DATABASE_URL`` is missing or any value is
    out of range. ``MAX_ROWS`` and ``STATEMENT_TIMEOUT_MS`` fall back to safe
    defaults when unset; ``DATABASE_URL`` has no default because a connection
    string with embedded credentials must never be baked into code.
    """
    env = os.environ if env is None else env
    return Settings(
        database_url=_required_str(env, "DATABASE_URL"),
        max_rows=_bounded_int(env, "MAX_ROWS", DEFAULT_MAX_ROWS, MAX_ROWS_LIMIT),
        statement_timeout_ms=_bounded_int(
            env, "STATEMENT_TIMEOUT_MS", DEFAULT_STATEMENT_TIMEOUT_MS, STATEMENT_TIMEOUT_MS_LIMIT
        ),
        log_level=_log_level(env, "LOG_LEVEL", DEFAULT_LOG_LEVEL),
    )
