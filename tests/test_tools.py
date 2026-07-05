"""Tests for the agent-facing tools (tools/)."""

import pytest

# TODO(M3): implement alongside the tools:
#   - list_tables returns the passengers table
#   - describe_table rejects table names outside the allow-list
#   - get_passenger returns a row / None for unknown ids
#   - search_passengers caps limit at settings.max_rows and rejects unknown filters
#   - survival_stats rejects group_by columns outside the allow-list


@pytest.mark.skip(reason="TODO(M3): tools not implemented yet")
def test_tools_reject_unvalidated_input() -> None:
    """Tool arguments outside the allow-lists must be rejected before any SQL is built."""
