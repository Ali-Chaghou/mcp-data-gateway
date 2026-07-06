# mcp-data-gateway

**Controlled, read-only access to PostgreSQL for AI agents — through a fixed set
of MCP tools, never a raw database connection.**

The gateway treats the agent as an untrusted client and puts every safety
guarantee in code and in the database, not in the agent's good behavior. It is a
focused reference implementation of a safe agent-to-database pattern on a small
public dataset.

## What this project proves

Each of these is demonstrated in code and checked in CI (see
[validation](validation.md)):

- A fixed MCP tool surface with **no raw-SQL-execution tool**.
- Every tool argument validated against allow-lists; values passed as bound
  parameters, never interpolated into SQL.
- A deny-by-default, read-only SQL guard in front of the driver.
- A read-only database session and a `SELECT`-only PostgreSQL role — the
  authoritative control — that refuse direct writes.
- JSON-safe output and one structured audit line per call, with no raw SQL or
  credentials.
- Continuous proof: lint, tests, audit, a strict docs build, live-database
  integration, and a non-root container image build.

## Explore

<div class="grid cards" markdown>

-   **Architecture**

    Components and the request path, with a rendered diagram.

    [Read →](architecture.md)

-   **Security model**

    The defense-in-depth layers and what each does not cover.

    [Read →](security-model.md)

-   **Implementation journey**

    How it was built, phase by phase, with the boundary of each step.

    [Read →](implementation-journey.md)

-   **Validation**

    What is actually proven, and by which tests and CI jobs.

    [Read →](validation.md)

-   **Production considerations**

    What is demonstrated versus what a real deployment still requires.

    [Read →](production-considerations.md)

-   **Demo walkthrough**

    Run the gateway locally with Docker.

    [Read →](demo-walkthrough.md)

</div>

## Scope and status

This shows the controls end to end; it is not a turnkey product. See
[production considerations](production-considerations.md) for exactly what is and
isn't provided.
