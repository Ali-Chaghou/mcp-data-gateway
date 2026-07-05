# Container image for the gateway server itself (optional — local development
# typically runs the server directly and only PostgreSQL in Docker).
FROM python:3.12-slim

# Run as a non-root user.
RUN useradd --create-home --uid 1000 gateway
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir .

USER gateway

# MCP over stdio: the container is meant to be launched by an MCP host.
ENTRYPOINT ["mcp-data-gateway"]
