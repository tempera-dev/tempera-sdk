# Remi and Tempera Code integration readiness

This records the current Remi `main` boundary. It is not evidence that a
hosted, principal-bound Tempera Code memory integration has been published.

## Ownership and transport

Tempera Code owns workflow dispatch, its durable journal/outbox, cancellation,
and bounded maintenance scheduling. The generated SDK owns portable operation
names, request shapes, and authentication transport. Current Remi `main`
accepts an explicit tenant/project scope under its service bearer; it does not
yet derive workspace identity from a central authenticated principal.

Do not bind Tempera Code with a path dependency or handwritten HTTP. Pin an
approved immutable SDK revision/package after this candidate has passed review
and publication gates.

## Generated operations available from current main

| Operation | Contract |
|---|---|
| `query` | `POST /v1/query`; `question`, explicit `scope`, and bounded retrieval controls. |
| `remember` | `POST /v1/remember`; explicit tenant/project identifiers, `kind`, redacted `text`, and optional idempotency key. |
| `project` | `POST /v1/project`; run the bounded projection pass. |
| `maintenance` | `POST /v1/maintenance`; run explicitly requested store maintenance. |

`context`, receipt-bound `feedback`, hosted principal-derived scope, and the
private Fabric MCP route existed only on an unmerged feature branch and are
not published from current Remi main. The SDK removes those phantom methods.

## Binding checklist

1. Do not bind Tempera Code to the current explicit-scope API as though it were
   a hosted principal-bound contract.
2. Land central principal binding, context receipts, and feedback validation in
   Remi first, together with its committed producer contract.
3. Regenerate the SDK from the exact Remi merge SHA and prove an authenticated
   E2E before enabling durable Code delivery.
4. Keep raw prompts, tool bodies, patches, command output, secrets, and browser
   content out of memory events.
