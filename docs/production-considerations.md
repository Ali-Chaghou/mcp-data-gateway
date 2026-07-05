# Production considerations

This page separates what the project demonstrates from what a regulated
production deployment would still require. It is deliberately honest: the gateway
is a reference implementation of a pattern, not a finished platform.

## Scope

`mcp-data-gateway` is a focused reference implementation of a controlled,
read-only MCP data gateway over PostgreSQL. It shows how to expose a small,
fixed set of read-only tools to an untrusted agent with defense in depth. It is
**not** a turnkey production platform, and running it as-is against sensitive
data would be premature.

## What is demonstrated

Concretely, and covered by tests and CI (see [validation](validation.md)):

- a fixed MCP tool surface with **no raw-SQL-execution tool**;
- input validation and allow-lists on every tool argument
  (see the [tool reference](tool-reference.md));
- a deny-by-default, read-only SQL guard;
- parameterized values — caller input is never interpolated into SQL;
- a read-only database session (`default_transaction_read_only = on`, statement
  timeout, row cap);
- a `SELECT`-only PostgreSQL role (`gateway_reader`);
- JSON-safe tool output;
- structured audit logging (one line per call, no raw SQL or credentials);
- live-database integration tests proving the role and session behavior;
- a container image that runs as a non-root user with no baked-in secrets;
- CI validation across code quality, docs, live-DB integration, and image build.

See the [architecture](architecture.md) and [security model](security-model.md)
for how these fit together.

## What this project does not provide

Out of scope here, and required thinking for real deployments:

- no row-level authorization;
- no column-level authorization;
- no multi-tenant isolation model;
- no external identity-provider integration;
- no production secret-manager integration;
- no network policy or firewall deployment;
- no backup/restore model;
- no high-availability or failover architecture;
- no rate limiting beyond the statement timeout and row cap;
- no full-SQL-parser guarantee (the guard is a heuristic filter);
- no data-classification model.

## Production hardening checklist

Before exposing real data through a gateway like this, address at least:

- **Database role** — provision a real least-privilege role through your own
  provisioning process, not the demo loader script.
- **Secrets** — use a secret manager instead of a local `.env` file.
- **Network** — restrict database access with network policy/firewall rules.
- **Data access model** — define row- and column-level access needs *before*
  exposing any data.
- **Audit logs** — route the structured logs to a central logging system.
- **Alerting** — alert on repeated validation failures or database errors.
- **Dependencies** — pin or lock dependencies.
- **Base images** — consider digest-pinning the container base image.
- **Image scanning** — add container vulnerability scanning to the pipeline.
- **Resilience** — define backup/restore and disaster-recovery expectations.
- **Ownership** — define ownership and operational runbooks.

## Honest risk framing

- The SQL guard is a **defense-in-depth filter, not the only boundary**. It
  reduces risk in front of the database; it does not replace it.
- The **database role and its permissions remain the control of record**. If the
  role can read something, the gateway can return it.
- A read-only gateway can still expose sensitive data if the role is too broad.
  Read-only is not the same as safe-to-expose.
- The most important production decision is the **data access model** — which
  rows and columns are readable, and by whom — not the MCP transport itself.

For the checks that back the demonstrated controls, see
[validation](validation.md); for day-to-day configuration and operation, see
[operations](operations.md).
