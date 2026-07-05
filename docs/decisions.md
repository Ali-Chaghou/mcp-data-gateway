# Decisions

Short, ADR-style summaries of the key design choices. The numbered records under
`docs/decision-records/` hold the full context for the foundational ones.

## Read-only, enforced in depth

Agents can only read, and that is enforced independently at the tool surface,
the SQL guard, the read-only session, and the `SELECT`-only role — so no single
failure enables a write. The database role is the authoritative layer.
See [ADR-0002](decision-records/0002-read-only-agent-access.md).

## PostgreSQL, single database

The gateway targets PostgreSQL specifically (roles, `default_transaction_read_only`,
statement timeouts) rather than a database-agnostic abstraction.
See [ADR-0001](decision-records/0001-use-postgresql.md).

## stdio-first MCP transport

The server speaks MCP over stdio and is launched by an MCP host, keeping the
process model simple and the attack surface small.
See [ADR-0003](decision-records/0003-stdio-first.md).

## The SQL guard is a filter, not a parser

`security/readonly_sql.py` is a deny-by-default heuristic that accepts only a
single `SELECT` over allow-listed tables. It is intentionally *not* a full SQL
parser; it is defense in depth in front of the database role, which remains the
control of record.

## Fixed tool surface, no raw SQL

Only six read-shaped tools are exposed, with table and column names as code
literals and all values parameterized. There is deliberately no
"run arbitrary SQL" tool.

## Serialize at the server boundary

`Decimal` values from PostgreSQL are converted to `float` in one place — the
server wrappers — so tool modules stay pure and the JSON concern lives where
output leaves for MCP. If exact decimal fidelity were ever required, the change
is `Decimal → str` in that single function.

## Audit at the server boundary

Every tool call is wrapped once to emit a structured audit line. Logging lives
at the boundary so all tools are covered uniformly, and raw SQL, result rows,
and credentials are never logged.

## Configuration from the environment

All settings are read and validated from environment variables; nothing
sensitive is committed or baked into the container image. `DATABASE_URL` is
required only at run time.
