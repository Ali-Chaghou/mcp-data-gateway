# Container image for the MCP gateway server.
#
# Runtime-only: installs the package with its runtime dependencies (mcp,
# psycopg); no dev tooling. All configuration (DATABASE_URL, MAX_ROWS, ...) is
# read from the environment at *run* time — nothing is baked in and the build
# requires no secrets or database.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Run as a dedicated non-root user.
RUN useradd --create-home --uid 1000 gateway

WORKDIR /app

# Copy only what the build needs; .dockerignore keeps .env, .git, caches, and
# local artifacts out of the build context entirely.
COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir .

USER gateway

# MCP over stdio: the container is meant to be launched by an MCP host, e.g.
#   docker run -i --rm -e DATABASE_URL=... mcp-data-gateway
# (No HEALTHCHECK: a stdio server has no port to probe; the host owns its lifecycle.)
ENTRYPOINT ["mcp-data-gateway"]
