# Architecture

## Overview

```
┌────────────┐   MCP (stdio)   ┌──────────────────────────────┐   SQL (read-only role)
│  AI agent  │ ◄─────────────► │  mcp-data-gateway (Python)  │ ◄────────────────────► PostgreSQL
│ (MCP host) │                 │                              │
└────────────┘                 │  server.py    tool registry  │
                               │  tools/       schema │ rows  │
                               │               │ aggregates   │
                               │  security/    readonly guard │
                               │  db.py        conn handling  │
                               │  config.py    env settings   │
                               └──────────────────────────────┘
```

The gateway is a single Python process speaking MCP over stdio (ADR-0003). Agents call
named tools; the gateway translates each call into a parameterized, validated SQL query
and returns structured results.

## Components

| Component                    | Responsibility                                                |
| ---------------------------- | ------------------------------------------------------------- |
| `server.py`                  | MCP server entrypoint; registers tools; stdio transport        |
| `config.py`                  | Typed settings loaded from the environment (`.env` in dev)     |
| `db.py`                      | psycopg connections; read-only session flags; timeouts         |
| `tools/schema.py`            | `list_tables`, `describe_table` — schema introspection         |
| `tools/passengers.py`        | Row lookup and filtered search over the demo dataset           |
| `tools/stats.py`             | Aggregate statistics (counts, group-bys, survival rates)       |
| `security/readonly_sql.py`   | Validates that outgoing SQL is a single read-only statement    |

## Request flow

1. The MCP host invokes a tool with JSON arguments.
2. Tool code validates arguments (types, ranges, allow-listed column names).
3. The tool builds a parameterized query and passes it through the read-only SQL guard.
4. `db.py` executes it on a `SELECT`-only role with `default_transaction_read_only=on`
   and a statement timeout.
5. Results are shaped into a compact JSON structure and returned to the agent.

## Safety model

Three independent layers must all fail before a write can occur — tool design, the SQL
guard, and database-role permissions. Details in [SECURITY.md](../SECURITY.md) and
ADR-0002.

## Data

The demo dataset is the Titanic passenger list, loaded by `scripts/load_titanic.py`
into a single `passengers` table. It is deliberately small so the focus stays on the
gateway pattern, not on data engineering.
