# Implementation journey

How the gateway was built, and why the main decisions were made. Each phase
follows the same shape: the problem, the decision, how it was implemented, how it
is validated, and the boundary — what the phase does *not* solve. Later phases
assume the earlier ones. This is written from the project's perspective, as a
reference for another engineer or team.

## 1. Define the safety boundary

- **Problem.** An agent with broad database access is risky: it may be
  prompt-injected, hallucinate queries, or misuse a wide capability.
- **Decision.** There is no raw-SQL MCP tool. Callers never run arbitrary SQL.
- **Implementation.** The MCP surface is a fixed set of read-shaped tools; table
  and column names are code literals, not caller input.
- **Validation.** Tests assert the registered tool set and that no
  arbitrary-SQL tool exists.
- **Boundary.** This controls the *shape* of access, not the sensitivity of the
  data behind it.

See the [security model](security-model.md) and [tool reference](tool-reference.md).

## 2. Add read-only SQL validation

- **Problem.** Even with fixed tools, tool code should never accidentally emit
  unsafe SQL.
- **Decision.** A deny-by-default read-only SQL guard sits in front of the
  driver.
- **Implementation.** `security/readonly_sql.py` accepts only a single `SELECT`
  over allow-listed tables, and rejects comments, statement chaining, quoted
  identifiers, and dangerous functions.
- **Validation.** The `readonly_sql` tests pin the accepted and rejected cases,
  including bypass classes (comma joins, subqueries, UNION, schema-qualified
  objects).
- **Boundary.** The guard is a heuristic filter, not a full SQL parser; it is
  defense in depth, not the control of record.

## 3. Move authority into PostgreSQL

- **Problem.** Application-level checks alone are not enough — a bug above the
  database should not be able to authorize a write.
- **Decision.** The authoritative control lives in PostgreSQL: a `SELECT`-only
  role and a read-only session.
- **Implementation.** `scripts/load_titanic.py` creates the `gateway_reader`
  role with `SELECT`-only grants and no write privileges; `db.py` opens sessions
  with `default_transaction_read_only = on`, a statement timeout, and a row cap.
- **Validation.** Live-DB integration tests and the smoke test prove a direct
  `INSERT` (bypassing the guard) is refused — both by the session and, via a raw
  connection, by the role's grants alone.
- **Boundary.** Readable data can still be exposed if the role is granted access
  to too much. Read-only is not the same as safe-to-expose.

See the [architecture](architecture.md) and [validation](validation.md).

## 4. Expose controlled MCP tools

- **Problem.** Generic database access is too broad a capability to hand an
  agent.
- **Decision.** Offer only schema inspection, passenger lookup/search, and
  aggregate statistics.
- **Implementation.** `tools/schema.py`, `tools/passengers.py`, and
  `tools/stats.py` validate arguments against allow-lists and pass values as
  bound parameters; `server.py` registers thin wrappers over them.
- **Validation.** Unit tests cover argument validation and parameterization; the
  smoke test and live-DB tests exercise the tools end to end.
- **Boundary.** The scope is intentionally one demo table and a focused tool set.

See the [tool reference](tool-reference.md).

## 5. Make outputs and operations safe

- **Problem.** MCP output must be JSON-serializable, and tool calls need a
  traceable record.
- **Decision.** A JSON-safe serialization boundary and a structured audit-logging
  boundary, both at the server wrappers.
- **Implementation.** `serialization.py` converts values such as `Decimal` to
  JSON-safe types without mutating source rows; `audit.py` emits one structured
  line per call — tool name, sanitized arguments, outcome, and a result count or
  error type — with no raw SQL, result rows, or credentials.
- **Validation.** Serialization and audit tests cover the conversions and assert
  secrets and `DATABASE_URL` are never logged.
- **Boundary.** These logs are a local trail, not a substitute for central
  observability in a real deployment.

See [operations](operations.md).

## 6. Prove the system continuously

- **Problem.** A local demo does not show that the controls hold repeatably.
- **Decision.** Enforce the gates in CI, including against a real database and a
  built image.
- **Implementation.** GitHub Actions jobs: quality (lint, test, audit), docs
  build, live-DB integration, and container image build.
- **Validation.** CI runs lint, tests, audit, a strict docs build, the live-DB
  integration tests, and a non-root container check on the built image.
- **Boundary.** CI proves this reference implementation; it does not stand in for
  a full production deployment.

See [validation](validation.md).

## 7. Document the architecture and limits

- **Problem.** Code alone does not explain design intent or the edges of the
  design.
- **Decision.** Maintain a documentation site covering architecture, security
  model, validation, operations, and production considerations.
- **Implementation.** MkDocs pages and a rendered architecture diagram.
- **Validation.** The docs build under MkDocs strict mode in CI, so broken links
  and missing pages fail the build.
- **Boundary.** Documentation is only useful while it stays aligned with the
  code; the strict build helps, but accuracy is an ongoing responsibility.

See the [production considerations](production-considerations.md) for what a
regulated deployment would still require, and the
[demo walkthrough](demo-walkthrough.md) to run it locally.
