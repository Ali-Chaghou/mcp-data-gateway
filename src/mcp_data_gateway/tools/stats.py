"""Aggregate statistics tools over the Titanic demo dataset."""

# TODO(M3): implement and register on the MCP server:
#   - survival_stats(group_by: str) -> survival counts/rates grouped by an
#     allow-listed column (pclass, sex, embarked)
#   - passenger_counts() -> total rows, per-class breakdown
#   group_by must be validated against the allow-list before query construction.


def survival_stats(group_by: str) -> list[dict]:
    """Return survival rates grouped by an allow-listed column."""
    raise NotImplementedError("TODO(M3)")
