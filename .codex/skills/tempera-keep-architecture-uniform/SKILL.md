---
name: tempera-keep-architecture-uniform
description: Check Tempera changes against shared service ownership, API, auth, state, storage, telemetry, maturity, and independent-program boundaries. Use before adding a service/resource, duplicating state, introducing an API/MCP surface, choosing storage, crossing repository ownership, or integrating Cyber or the central Workflows/UI program.
---

# Tempera Architecture Guard

## Decision test

Before implementation, answer:

1. Which service owns the durable resource and state transitions?
2. Which committed source contract defines it?
3. Which consumers derive clients/tools/views from it?
4. What actor/org/project/environment/audience/scopes/revocation bind the action?
5. What are idempotency, retry, cancellation, pagination, error, retention, and migration semantics?
6. What proves local, integrated, staging, and production maturity?
7. Is it general platform capability, independent Workflows/UI product work, Cyber/domain work, or another side program?
8. What is the compatibility and rollback plan?

If ownership remains ambiguous, write a short ADR and stop. Do not create a new service or duplicate data to escape the decision.

## Required invariants

- Thin binaries over library-owned behavior.
- Handler/contract parity and derived SDK/MCP surfaces.
- One durable owner; others keep immutable references, projections, or caches.
- Fail-closed central auth and tenant isolation.
- Structured logs, W3C traces, metrics, health, version, dependency readiness, usage/cost receipts where relevant.
- SQLite only for local embedded state; PostgreSQL for relational control plane; ClickHouse for trace/event analytics; object storage for large immutable artifacts, absent an approved ADR.
- Explicit contract-only/local/integrated/staging-qualified/production-qualified maturity.

Read [ownership-and-boundaries.md](references/ownership-and-boundaries.md) for the service map and independent-program rules.
