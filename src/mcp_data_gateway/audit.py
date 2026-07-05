"""Structured audit logging for tool invocations.

Every MCP-exposed tool call is wrapped by :func:`audited`, which emits exactly
one structured log line: the tool name, its sanitized arguments, the outcome
(success or error), and a row/result count or error type. Lines are key=value
with JSON-encoded values so they are unambiguous and easy to grep, e.g.::

    tool="get_passenger" outcome="success" result_count=1 args={"passenger_id": 1}

Only tool arguments are logged. Settings (including ``DATABASE_URL``), the SQL
text, and result rows are never passed in, and a sensitive-key denylist drops
anything that looks like a credential as defense in depth.
"""

import json
import logging
from collections.abc import Callable
from typing import Any

from mcp_data_gateway.config import Settings

_ROOT_LOGGER_NAME = "mcp_data_gateway"
_AUDIT_LOGGER_NAME = "mcp_data_gateway.audit"

# Argument keys never worth logging; tool wrappers don't pass these, but drop
# them anyway so a future caller can't leak a credential through the audit log.
_SENSITIVE_KEYS = ("password", "secret", "token", "database_url", "dsn", "conn", "key")


def get_logger() -> logging.Logger:
    return logging.getLogger(_AUDIT_LOGGER_NAME)


def configure_logging(settings: Settings) -> None:
    """Set up the package logger to emit to stderr at ``settings.log_level``.

    Safe to call once at startup; it will not attach duplicate handlers.
    """
    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.setLevel(settings.log_level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in _SENSITIVE_KEYS)


def _sanitize(args: dict[str, Any]) -> dict[str, Any]:
    """Keep only non-null, non-sensitive arguments for logging."""
    return {k: v for k, v in args.items() if v is not None and not _is_sensitive(k)}


def _result_count(result: Any) -> int:
    if result is None:
        return 0
    if isinstance(result, list):
        return len(result)
    return 1


def _render(fields: dict[str, Any]) -> str:
    return " ".join(f"{key}={json.dumps(value)}" for key, value in fields.items())


def audited[T](tool: str, args: dict[str, Any], call: Callable[[], T]) -> T:
    """Run ``call``, emit one audit log line, and return (or re-raise).

    Preserves the original exception: validation and database errors are logged
    with their type and then propagate unchanged.
    """
    logger = get_logger()
    safe_args = _sanitize(args)
    try:
        result = call()
    except Exception as exc:
        logger.info(
            _render(
                {
                    "tool": tool,
                    "outcome": "error",
                    "error_type": type(exc).__name__,
                    "args": safe_args,
                }
            )
        )
        raise
    logger.info(
        _render(
            {
                "tool": tool,
                "outcome": "success",
                "result_count": _result_count(result),
                "args": safe_args,
            }
        )
    )
    return result
