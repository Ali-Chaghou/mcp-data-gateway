"""End-to-end smoke test.

Exercises the full stack (MCP server over stdio -> guard -> PostgreSQL) the way
an agent host would, and fails loudly if anything is broken.

Usage:
    python scripts/smoke_test.py
"""

# TODO(M3): implement using the MCP Python client:
#   1. spawn the server as a stdio subprocess
#   2. list tools; assert the expected tool names are present
#   3. call list_tables, get_passenger, survival_stats and sanity-check results
#   4. assert that no write-shaped tool exists
#   5. exit non-zero on any failure


def main() -> None:
    raise NotImplementedError("TODO(M3): smoke test not implemented yet")


if __name__ == "__main__":
    main()
