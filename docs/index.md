# mcp-data-gateway

A small, production-minded [MCP](https://modelcontextprotocol.io) server that
lets AI agents query a PostgreSQL database through a fixed set of **controlled,
read-only tools** — never a raw database connection.

The guiding idea: treat the agent as an untrusted client and put every safety
guarantee in the gateway and the database, not in the agent's good behavior.

## What it does

- Exposes six read-only tools over MCP stdio: `list_tables`, `describe_table`,
  `get_passenger`, `search_passengers`, `survival_summary`, `survival_by`.
- Validates every argument against allow-lists and passes values as bound
  parameters — never string-interpolated into SQL.
- Runs each query through a deny-by-default SQL guard, a read-only database
  session, and a `SELECT`-only database role.
- Logs one structured audit line per tool call, without raw SQL or credentials.

## Where to go next

- [Architecture](architecture.md) — the components and the request path.
- [Security model](security-model.md) — the defense-in-depth layers.
- [Validation](validation.md) — what is actually proven, and how.
- [Demo walkthrough](demo-walkthrough.md) — run it locally with Docker.
- [Decisions](decisions.md) — the key design choices.

## Scope and status

This is a focused reference implementation of a safe agent-to-database pattern
on a small public dataset. It demonstrates the controls end to end; it is not a
turnkey multi-tenant product. See [Validation](validation.md) for exactly what
is and isn't proven.
