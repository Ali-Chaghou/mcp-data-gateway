# Engineering process

How this repository is developed and what "done" means.

## Principles

- **Security decisions are explicit.** Anything that affects the safety model is
  written down — in SECURITY.md, in a decision record, or in a test that pins the
  behavior.
- **Small steps, always green.** Each change keeps `make lint` and `make test`
  passing. Milestones (docs/project-plan.md) are merged incrementally, not as one
  big drop. Scaffold-only commits may contain skipped or xfail tests when those
  tests document upcoming behavior — the suite as a whole must still pass.
- **Tests before trust.** The read-only SQL guard is developed test-first; its test
  suite is the authoritative specification of what SQL is allowed through.
- **No cleverness without a reason.** Prefer the standard library and boring,
  auditable dependencies.

## Workflow

1. Work happens on short-lived branches; `main` stays releasable.
2. Every commit passes pre-commit hooks (ruff, bandit, hygiene checks).
3. Design-level choices get an ADR in `docs/decision-records/` before or with the
   implementation.
4. TODOs in code reference the milestone they belong to.

## Quality gates

| Gate            | Tool          | Command       |
| --------------- | ------------- | ------------- |
| Lint & format   | ruff          | `make lint`   |
| Tests           | pytest        | `make test`   |
| Static security | bandit        | `make audit`  |
| Dependency CVEs | pip-audit     | `make audit`  |
| Git hooks       | pre-commit    | automatic     |

## Decision records

ADRs follow a lightweight format: context, decision, consequences. Numbered
sequentially, never rewritten — superseded decisions get a new record.
