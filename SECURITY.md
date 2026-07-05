# Security

## Threat model

The primary risk in an agent-to-database gateway is that an LLM agent — whether
misbehaving, prompt-injected, or simply confused — issues a query that modifies or
destroys data, or reads data it should not.

This project treats the agent as an **untrusted client**. All safety guarantees live in
the gateway and the database, never in the agent's good behavior.

## Defense in depth

The intended runtime model enforces read-only access at three independent layers.
The tool surface is a design commitment already reflected in the repository, and the
SQL guard (layer 2) is implemented. The database-role setup (layer 3) — which is the
authoritative enforcement layer — is scheduled for milestone M2 (see
[docs/project-plan.md](docs/project-plan.md)) and is described here as the target state,
not yet a shipped control. Until it lands, the SQL guard is the only active runtime
control.

1. **Tool design.** The MCP tools expose only narrow read operations (describe schema,
   look up rows, compute aggregates). There is no tool whose purpose is to execute
   arbitrary write statements.
2. **SQL guard** (`src/mcp_data_gateway/security/readonly_sql.py`). Any SQL that
   reaches the database driver is validated first: single statement only, must be a
   `SELECT`, no data-modifying or DDL keywords, no statement chaining, no comments,
   only allow-listed tables, and a denylist of dangerous functions. This guard is a
   **deny-by-default first filter, not a complete SQL parser** — it is a heuristic that
   errs toward rejection, and it is intentionally not relied on as the sole guarantee
   of read-only or table access.
3. **Database role** (planned for M2, and the authoritative layer). The server connects
   as a dedicated PostgreSQL role that holds `SELECT`-only grants, is not granted
   `EXECUTE` on dangerous functions, and runs sessions with
   `default_transaction_read_only = on`. This is what ultimately enforces read-only and
   table-level access: even if layers 1 and 2 fail or are bypassed, the database refuses
   writes and access to tables the role cannot read.

Additional practices:

- Parameterized queries everywhere; user/agent input is never interpolated into SQL
  (a rule for all upcoming implementation work).
- Configuration and credentials come from the environment; nothing sensitive is
  committed (see `.env.example`).
- Static analysis (`bandit`) and dependency auditing (`pip-audit`) run locally via
  pre-commit and `make audit`; a CI pipeline running the same gates is planned
  (milestone M4).

## What this project does not defend against

- Exfiltration of data the read-only role *is* allowed to read — data-level access
  control is a deployment concern (row-level security, views, or a restricted schema).
- Denial of service via expensive queries. Statement timeouts are planned
  (see docs/project-plan.md) but result-set limits are already part of the tool design.

## Reporting a vulnerability

Please open a GitHub security advisory (or a private issue) rather than a public issue.
Reports will be acknowledged within a few days.
