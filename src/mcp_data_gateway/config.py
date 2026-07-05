"""Environment-based configuration.

All settings come from the environment (``.env`` in local development); nothing
sensitive lives in code.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the gateway."""

    database_url: str
    statement_timeout_ms: int = 5000
    max_rows: int = 200


def load_settings() -> Settings:
    """Load settings from the environment.

    TODO(M2): validate values (positive timeouts, sane row limits) and fail fast
      with a clear message when DATABASE_URL is missing.
    """
    return Settings(
        database_url=os.environ["DATABASE_URL"],
        statement_timeout_ms=int(os.environ.get("GATEWAY_STATEMENT_TIMEOUT_MS", "5000")),
        max_rows=int(os.environ.get("GATEWAY_MAX_ROWS", "200")),
    )
