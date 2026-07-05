# Demo walkthrough

Run the gateway locally against a Dockerized PostgreSQL. Requires Python 3.12,
Docker, and `make`.

## 1. Configure

```sh
cp .env.example .env      # defaults are for local development only
```

The defaults start PostgreSQL on port **5432** and point `DATABASE_URL` at the
`gateway_reader` role. If port 5432 is already used by a local PostgreSQL, use
**5433** instead — edit `.env`:

```dotenv
POSTGRES_PORT=5433
DATABASE_URL=postgresql://gateway_reader:gateway_reader_dev_password@localhost:5433/agentdata
```

`docker-compose.yml` maps `${POSTGRES_PORT}:5432`, so the container still listens
on 5432 internally while the host uses 5433; the loader and server both read the
port from `.env`, so no other change is needed.

## 2. Start the stack

```sh
make up           # start PostgreSQL via Docker Compose
make install      # create the venv and install the project
make load-data    # create the schema + sample data + gateway_reader role
```

`make load-data` connects as the local admin only for setup, then creates the
`SELECT`-only `gateway_reader` role that the server actually uses.

## 3. Verify and run

```sh
make smoke        # end-to-end checks, including that direct writes are refused
make run          # start the MCP server on stdio
```

To use it from an MCP-capable client, register a stdio server pointing at
`python -m mcp_data_gateway.server` (or the `mcp-data-gateway` console script).

## 4. Run in a container (optional)

```sh
docker build -t mcp-data-gateway:local .
docker run -i --rm -e DATABASE_URL=... mcp-data-gateway:local
```

The image is runtime-only and runs as a non-root user. It reads all
configuration from the environment; nothing is baked in.

## Clean up

```sh
make down         # stop PostgreSQL
```
