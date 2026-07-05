"""Agent-facing MCP tools.

Every tool here is read-only by design (ADR-0002). Tools validate their own
arguments and only ever emit parameterized SQL through the database layer.
"""
