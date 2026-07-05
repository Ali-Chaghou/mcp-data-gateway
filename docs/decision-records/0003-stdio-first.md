# ADR-0003: stdio transport first

**Status:** accepted · **Date:** 2026-07-05

## Context

MCP supports multiple transports, most notably stdio (the client launches the server
as a subprocess) and streamable HTTP (the server runs as a network service). Each
brings different operational and security surface.

## Decision

Ship the stdio transport first. HTTP is a possible later addition (milestone M4), not
part of the initial scope.

## Consequences

- stdio is the default integration path for desktop MCP hosts and IDE integrations,
  so the server is immediately usable where agents actually run today.
- No network listener means no authentication, TLS, or session management to get
  right in v1 — the attack surface is the local process boundary.
- One server process per client is acceptable at this scale; connection pooling
  across many clients becomes relevant only with an HTTP transport.
- The tool layer is transport-agnostic, so adding HTTP later is additive and does not
  reopen the security design.
