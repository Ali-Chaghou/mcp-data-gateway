# Architecture

The gateway is a single Python process that speaks MCP over stdio (ADR-0003).
An MCP host/client calls named tools; each call is validated, turned into a
parameterized read-only query, executed against PostgreSQL through a hardened
session, and returned as JSON-safe data. This page describes the system as it is
built today.

> A rendered architecture diagram is planned separately; this page is the
> authoritative textual description.

## Request path

```
MCP host / client
      │  (stdio, JSON tool calls)
      ▼
server.py            MCP tool wrappers (fixed surface, no raw-SQL tool)
      │
      ├─ audit.py            audit-logging boundary: one structured line per call
      ├─ serialization.py    JSON-safe boundary: Decimal → float, recursive
      │
      ▼
tools/               schema.py · passengers.py · stats.py
      │              (argument allow-lists; parameterized values only)
      ▼
security/readonly_sql.py   read-only SQL guard (single SELECT, allow-listed tables)
      │
      ▼
db.py                execute_readonly: read-only session + statement timeout + row cap
      │  (SQL, read-only role)
      ▼
PostgreSQL           passengers table, queried by the gateway_reader SELECT-only role
```

## Components

| Component | Responsibility |
| --- | --- |
| `server.py` | Registers the six MCP tools over stdio; each wrapper is thin and applies the audit and serialization boundaries. |
| `audit.py` | Emits one structured log line per tool call (name, sanitized args, outcome, count/error type). No raw SQL or credentials. |
| `serialization.py` | Converts tool output to JSON/MCP-safe values (notably `Decimal` → `float`), recursively and without mutating source rows. |
| `tools/schema.py` | `list_tables`, `describe_table` — curated metadata for the allow-listed table. |
| `tools/passengers.py` | `get_passenger`, `search_passengers` — validated, parameterized lookups. |
| `tools/stats.py` | `survival_summary`, `survival_by` — aggregates over fixed query templates. |
| `security/readonly_sql.py` | Deny-by-default guard: a single `SELECT`, allow-listed tables, no comments/chaining/dangerous functions. |
| `db.py` | psycopg connections with `default_transaction_read_only = on`, a statement timeout, and a result-row cap. |
| `config.py` | Typed settings loaded and validated from the environment. |

## Runtime and database

The server connects as **`gateway_reader`**, a PostgreSQL role created by
`scripts/load_titanic.py` with `SELECT`-only grants on `passengers` and no write
privileges (ADR-0002). The demo dataset is a small, deterministic Titanic-style
`passengers` table, kept intentionally small so the focus stays on the gateway
pattern rather than data engineering.

## Continuous integration

CI (GitHub Actions) has three jobs:

- **quality** — `make lint`, `make test`, `make audit` (ruff, pytest, bandit, pip-audit); no database.
- **integration** — a PostgreSQL service container; runs `make load-data`, `make smoke`, and the opt-in live-DB tests.
- **image** — builds the container image and runs an import-only sanity check plus a non-root assertion; no database.
