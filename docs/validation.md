# Validation

What the project actually proves, and how. The aim is honesty: each control has
a corresponding check.

## Unit tests

Fast, database-free tests (run by `make test`) cover:

- the read-only SQL guard, including bypass classes (comma joins, subqueries,
  UNION, schema-qualified objects, dangerous functions, statement chaining);
- argument validation and rejection for every tool, before any SQL is issued;
- parameterization — values are passed as bound parameters, not interpolated;
- the database layer's guard call, row-limit application, and read-only session
  setup, using a fake connection;
- JSON-safe serialization (`Decimal → float`, recursive, non-mutating);
- audit logging (one line per call; secrets and `DATABASE_URL` never logged);
- MCP tool registration and wrapper behavior.

## Smoke test

`make smoke` runs the tools end to end against a running stack and checks sane
results, including a direct `INSERT` (bypassing the guard) that the database
must refuse. It exits with a clear setup message — not a stack trace — when the
database or configuration is missing.

## Live-DB integration tests

Opt-in tests (enabled by `MCP_GATEWAY_RUN_INTEGRATION=1`) prove against real
PostgreSQL that:

- the configured read-only session refuses a direct write while reads work;
- `gateway_reader` is `SELECT`-only — a raw connection's `INSERT` fails with
  insufficient privilege, proving the role independently of the session;
- the schema, passenger-lookup, and stats tools return correct results.

They are skipped by a normal `make test`, and run in the CI **integration** job
against a PostgreSQL service container.

## Docker image build

The CI **image** job builds the container image with no database and no secrets,
then runs an import-only sanity check (`import mcp_data_gateway.server`) with the
entrypoint overridden so the stdio server does not hang.

## Non-root container check

The same job asserts the image runs as the unprivileged `gateway` user by
checking `id -un` inside the container.
