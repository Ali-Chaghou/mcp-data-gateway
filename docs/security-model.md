# Security model

The threat is an untrusted agent: it may be prompt-injected, may hallucinate
queries, or may try to misuse a broad capability. The gateway assumes that and
places every guarantee in code and in the database — never in the agent.

## Defense in depth

Several independent layers each have to fail before anything unsafe happens.

1. **No raw-SQL tool.** There is no tool that executes caller-supplied SQL. The
   only surface is a fixed set of read-shaped tools.
2. **Fixed tool surface.** Exactly six tools are registered. Table and column
   names are string literals in code, never taken from caller input.
3. **Argument validation.** Each tool validates its arguments against explicit
   allow-lists (e.g. `pclass ∈ {1,2,3}`, `group_by ∈ {pclass, sex, embarked}`)
   before any SQL is built. Values are always bound as parameters.
4. **Read-only SQL guard.** `security/readonly_sql.py` is a deny-by-default
   filter: it accepts only a single `SELECT`, over allow-listed tables, with no
   comments, no statement chaining, and no dangerous functions. It is a
   heuristic first filter, **not** a full SQL parser.
5. **Read-only database session.** Every connection sets
   `default_transaction_read_only = on` and a statement timeout, so a write that
   somehow reached the driver is still refused.
6. **`SELECT`-only role.** The server connects as `gateway_reader`, which holds
   `SELECT`-only grants on `passengers` and no write privileges. This is the
   authoritative control: even if the layers above were bypassed, the database
   refuses the write.

The database role is the layer of record. The guard and session are defense in
depth in front of it, not a substitute for it.

## Secrets

- No secrets are baked into the container image; `.env` and `.venv` are excluded
  from the build context, and all configuration is read from the environment at
  run time.
- `DATABASE_URL` is required at run time only — it is never needed to build the
  image and is never written to logs.

## Audit logging

Every tool call emits one structured, greppable log line: tool name, sanitized
arguments, outcome (success/error), and a result count or error type. Raw SQL,
result rows, `DATABASE_URL`, and any credential-shaped argument are never
logged; a sensitive-key denylist drops the latter as defense in depth.

## What this does not defend against

- Exfiltration of data the read-only role is *allowed* to read — column- and
  row-level access control is a deployment concern (views, RLS, or a restricted
  schema), out of scope for this demo.
- Denial of service via expensive queries beyond the statement timeout and row
  cap.
