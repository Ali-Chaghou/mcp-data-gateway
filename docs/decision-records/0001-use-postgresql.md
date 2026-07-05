# ADR-0001: Use PostgreSQL as the backing database

**Status:** accepted · **Date:** 2026-07-05

## Context

The gateway needs a relational database that supports fine-grained, role-based access
control, since the security model relies on a database-enforced read-only role as its
last line of defense. The project should also demonstrate patterns that transfer to
real production systems.

## Decision

Use PostgreSQL (via Docker Compose for local development), accessed with psycopg 3.

## Consequences

- `GRANT SELECT`-only roles and `default_transaction_read_only` give us a hard,
  database-enforced read-only guarantee — SQLite, for comparison, has no role system.
- PostgreSQL is ubiquitous in production, so the pattern shown here is directly
  reusable.
- We accept the operational dependency on Docker for local development; SQLite would
  have been zero-setup but weakens the security story.
- Single-database scope: supporting other engines is an explicit non-goal.
