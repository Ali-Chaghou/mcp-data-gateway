"""Opt-in marker for live-database integration tests.

These tests need a running PostgreSQL with the schema, sample data, and the
``gateway_reader`` role in place (``make up`` + ``make load-data``). They are
skipped unless ``MCP_GATEWAY_RUN_INTEGRATION=1`` is set, so a normal
``make test`` stays fast and DB-free. The CI integration job sets that variable.
"""

import os

import pytest

RUN_INTEGRATION = os.environ.get("MCP_GATEWAY_RUN_INTEGRATION") == "1"

requires_integration = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="live-DB test; set MCP_GATEWAY_RUN_INTEGRATION=1 (see the CI integration job)",
)
