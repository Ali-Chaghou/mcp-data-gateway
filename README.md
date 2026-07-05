# mcp-data-gateway

[![CI](https://github.com/Ali-Chaghou/mcp-data-gateway/actions/workflows/ci.yml/badge.svg)](https://github.com/Ali-Chaghou/mcp-data-gateway/actions/workflows/ci.yml)

A production-minded [MCP](https://modelcontextprotocol.io) server that lets AI agents
query a PostgreSQL database through a small set of **controlled, read-only tools**.

The core idea: agents never get raw database access. Every interaction goes through
explicitly designed tools with validated inputs and a read-only SQL guard, backed by
a least-privilege database role as the authoritative enforcement layer.

> **Status:** in progress. The config, database layer, SQL guard, and data loader are
> implemented, and the schema, passenger-lookup, and stats tools are exposed over the
> FastMCP stdio server. An end-to-end smoke test and further hardening remain. See
> [docs/project-plan.md](docs/project-plan.md).

## Why

Giving an LLM agent a database connection string is easy — and dangerous. This project
demonstrates a safer pattern:

- **Read-only by design** — three independent layers: tool design, a SQL validation
  guard as defense-in-depth, and a least-privilege database role as the authoritative
  control. The guard is a deny-by-default first filter, not a full SQL parser; the
  database role/session (`SELECT`-only, `default_transaction_read_only`) is what
  ultimately enforces read-only and table access, and is planned for M2. See
  [SECURITY.md](SECURITY.md).
- **Small, purposeful tool surface** — schema inspection, row lookup, and aggregate
  stats. No generic "run any SQL" escape hatch for write operations.
- **Boring, auditable stack** — Python 3.12, psycopg, PostgreSQL, Docker Compose.

The demo dataset is the classic Titanic passenger list: small, well-known, and
suitable as a low-risk public demo dataset.

## Quickstart

Requires Python 3.12+, Docker, and `make`.

```sh
cp .env.example .env        # defaults work for local development
make up                     # start PostgreSQL via Docker Compose
make install                # create venv and install dependencies
make load-data              # create the schema, load sample data, set up the reader role
make run                    # start the MCP server on stdio
```

`make load-data` connects as the local admin (`POSTGRES_*`) only for setup: it
creates the `passengers` table with a small deterministic sample, then creates
the `gateway_reader` role with `SELECT`-only access. The server itself connects
via `DATABASE_URL`, which points at `gateway_reader` — never the admin user. The
script is idempotent, so you can re-run it safely.

To use with an MCP-capable client, register the server with a stdio transport
pointing at `python -m mcp_data_gateway.server`.

## Repository layout

```
src/mcp_data_gateway/
  server.py            # MCP server entrypoint (stdio)
  config.py            # environment-based configuration
  db.py                # connection handling
  tools/               # the agent-facing tools
    schema.py          #   describe tables and columns
    passengers.py      #   look up passenger rows
    stats.py           #   aggregate statistics
  security/
    readonly_sql.py    # read-only SQL guard
scripts/               # data loading and smoke test
tests/                 # pytest suite
docs/                  # architecture, process, decision records
```

## Documentation

Full documentation lives in [`docs/`](docs/index.md) and builds into a static
site with MkDocs:

- [Architecture](docs/architecture.md) — components and the request path
- [Security model](docs/security-model.md) — the defense-in-depth layers
- [Tool reference](docs/tool-reference.md) — the six MCP tools in detail
- [Operations](docs/operations.md) — configuration, container, logs, commands
- [Validation](docs/validation.md) — what is proven, and how
- [Demo walkthrough](docs/demo-walkthrough.md) — run it locally with Docker
- [Decisions](docs/decisions.md) — key design choices

```sh
make docs               # build the site into site/
make docs-serve         # preview locally with live reload
```

## Development

```sh
make test               # run pytest
make lint               # ruff check + format check
make audit              # bandit + pip-audit
pre-commit install      # enable git hooks
```

Engineering conventions are described in
[docs/engineering-process.md](docs/engineering-process.md); design decisions are
captured as ADRs in [docs/decision-records/](docs/decision-records/).

## License

MIT
