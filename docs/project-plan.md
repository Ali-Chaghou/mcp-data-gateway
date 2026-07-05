# Project plan

Goal: a production-minded MCP server that lets AI agents safely query a PostgreSQL
database through controlled, read-only tools.

## Milestones

### M1 — Repository foundation ✅ (current)

- Repository layout, packaging (`pyproject.toml`), Docker Compose for PostgreSQL.
- Quality tooling: ruff, pytest, bandit, pip-audit, pre-commit.
- Design docs and decision records.
- Module skeletons with TODOs; no behavior yet.

### M2 — Database layer and read-only guard

- `config.py`: environment-based settings with validation.
- `db.py`: psycopg connection handling, read-only session setup, statement timeout.
- `security/readonly_sql.py`: the SQL validation guard, fully tested
  (`tests/test_readonly_sql.py` is the spec).
- `scripts/load_titanic.py`: schema creation + Titanic CSV load, plus a
  `SELECT`-only role for the server.

### M3 — MCP tools

- `tools/schema.py`: `list_tables`, `describe_table`.
- `tools/passengers.py`: `get_passenger`, `search_passengers` (filtered, paginated).
- `tools/stats.py`: `survival_stats`, grouped aggregates.
- `server.py`: register tools on a stdio MCP server.
- `scripts/smoke_test.py`: end-to-end check against a running stack.

### M4 — Hardening and polish

- CI workflow (lint, tests, audit).
- Structured logging of every tool invocation (audit trail).
- Container image for the server itself; optional HTTP transport.
- Load/error-path tests; statement timeout and row-limit tuning.

## Non-goals

- Write access of any kind for agents.
- A generic "execute arbitrary SQL" tool surface.
- Multi-database support (PostgreSQL only — see ADR-0001).
