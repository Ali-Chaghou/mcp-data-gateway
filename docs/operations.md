# Operations

How to configure, run, and observe the gateway. For a step-by-step first run,
see the [demo walkthrough](demo-walkthrough.md).

## Runtime configuration

All configuration comes from the environment and is validated at startup; the
process fails fast with a clear message on a bad value.

| Variable | Required | Default | Rules |
| --- | --- | --- | --- |
| `DATABASE_URL` | yes | — | connection string for the runtime role (`gateway_reader`) |
| `MAX_ROWS` | no | `200` | positive integer, at most `10000` |
| `STATEMENT_TIMEOUT_MS` | no | `5000` | positive integer, at most `60000` |
| `LOG_LEVEL` | no | `INFO` | one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

`DATABASE_URL` is required only at run time — it is never needed to build the
container image. `MAX_ROWS` is the ceiling on rows any tool returns;
`STATEMENT_TIMEOUT_MS` bounds each query at the database session.

## Local Docker usage

A local PostgreSQL often already listens on **5432**. The project can run on
**5433** instead — set both the mapped port and the connection string in `.env`:

```dotenv
POSTGRES_PORT=5433
DATABASE_URL=postgresql://gateway_reader:gateway_reader_dev_password@localhost:5433/agentdata
```

`docker-compose.yml` maps `${POSTGRES_PORT}:5432`, so the container still listens
on 5432 internally while the host uses 5433. The loader and server read the port
from `DATABASE_URL`/`POSTGRES_PORT`, so nothing else changes.

## Container usage

The image runs the **stdio** MCP server, so it is meant to be launched by an MCP
host and given its configuration through environment variables:

```sh
docker build -t mcp-data-gateway:local .
docker run -i --rm -e DATABASE_URL=... mcp-data-gateway:local
```

- The image runs as the non-root `gateway` user.
- No secrets are baked in — `.env` and `.venv` are excluded from the build
  context, and all configuration is read from the environment at run time.
- The build itself needs no `DATABASE_URL` and no database.

## Audit logs

Every tool call emits exactly **one** structured, greppable log line at `INFO`,
for example:

```
tool="get_passenger" outcome="success" result_count=1 args={"passenger_id": 1}
tool="survival_by" outcome="error" error_type="InvalidGroupByError" args={"group_by": "name"}
```

Each line carries the tool name, the sanitized arguments, the outcome
(`success`/`error`), and either a `result_count` or an `error_type`. Raw SQL,
result rows, `DATABASE_URL`, and any credential-shaped argument are **never**
logged. Verbosity follows `LOG_LEVEL`.

## Validation commands

| Command | What it checks |
| --- | --- |
| `make lint` | ruff lint + format check |
| `make test` | fast, database-free unit tests |
| `make audit` | bandit static analysis + pip-audit dependency scan |
| `make docs` | MkDocs strict build (fails on broken links or nav gaps) |
| `make smoke` | end-to-end checks against a running stack |
| `MCP_GATEWAY_RUN_INTEGRATION=1 make test` | also runs the opt-in live-DB tests |

`make smoke` prints a short setup hint (not a stack trace) when the database or
configuration is missing. See [validation](validation.md) for what each check
proves, and the [security model](security-model.md) for the controls behind
them.
