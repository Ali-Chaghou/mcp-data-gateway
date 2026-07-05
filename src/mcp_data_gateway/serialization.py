"""JSON/MCP-safe serialization of tool results.

PostgreSQL ``numeric`` columns (here: ``age`` and ``fare``) come back from
psycopg as :class:`decimal.Decimal`, which the JSON layer MCP uses cannot
serialize. :func:`json_safe` normalizes tool output just before it leaves the
server.

Decimal is converted to ``float``. For this demo dataset — ages, fares, and
survival rates — a float is the natural JSON type and the small precision loss
is irrelevant. If exact decimal fidelity ever mattered (e.g. real money), the
right change is to convert to ``str`` instead, in this one place.
"""

from decimal import Decimal
from typing import Any


def json_safe(value: Any) -> Any:
    """Return a JSON-safe copy of ``value``.

    ``Decimal`` becomes ``float``; ``dict`` and ``list``/``tuple`` are rebuilt
    recursively into new containers (the input is never mutated); everything
    else is returned unchanged.
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [json_safe(item) for item in value]
    return value
