# ADR-0002: Agents get read-only access, enforced in depth

**Status:** accepted · **Date:** 2026-07-05

## Context

An LLM agent is an untrusted client: it can be prompt-injected, hallucinate queries,
or misuse a broad capability. Any write path exposed to an agent is a write path
exposed to whoever controls the agent's input.

## Decision

Agents can only read. This is enforced at three independent layers:

1. **Tool surface** — only read-shaped tools exist (schema inspection, row lookup,
   aggregates). No tool executes caller-supplied write statements.
2. **SQL guard** — `security/readonly_sql.py` rejects anything that is not a single
   `SELECT` statement before it reaches the driver.
3. **Database role** — the server's PostgreSQL role has `SELECT`-only grants and
   `default_transaction_read_only = on`.

## Consequences

- A single bug (or a single bypassed layer) cannot produce a write; all three layers
  would have to fail together.
- Use cases requiring writes (e.g. agents recording annotations) are out of scope and
  would need a separate, differently-designed pathway — not a loosening of this one.
- The SQL guard adds a maintenance cost: it must be conservative (deny by default)
  and is pinned by a dedicated test suite.
