# Remi ↔ Tempera Code integration readiness

This is the binding checklist for the durable Remi lifecycle path. It is a
release-readiness record, not evidence that the runtime integration is live.

## Intended path and ownership

```
Tempera Code workflow / CLI / app-server
  -> versioned generated Tempera SDK transport
    -> authenticated Remi API
```

- Tempera Code owns workflow dispatch, the durable journal/outbox,
  cancellation, and bounded maintenance scheduling.
- The SDK owns the generated operation names, request shape, authentication
  header transport boundary, and package version that makes the contract
  portable.
- Remi derives memory scope from the authenticated principal and owns
  retrieval receipts, evidence validation, feedback acceptance, and ledger
  truth.
- Auth Hub retains the `remi` audience. It must not turn this lifecycle into
  public hosted `remi_*` MCP discovery.

## Required generated contract

The SDK must expose these authenticated `remi` operations from `surface.json`:

| Operation | Method and path | Required fields | Rules |
|---|---|---|---|
| `context` | `POST /v1/context` | `question` | Optional `max_tokens`, `modes`; no client-supplied tenant, project, or workspace scope. Response must carry a fresh retrieval receipt and cited evidence. |
| `recordObservation` | `POST /v1/observations` | `kind`, `summary`, `artifact_refs`, `trace_id`, `idempotency_key` | Summary is bounded/redacted; references are opaque. `checkpoint_ref` is optional. Never send prompts, tool bodies, patch bodies, command output, secrets, or browser content. |
| `feedback` | `POST /v1/feedback` | `retrieval_receipt_id`, `evidence_node_id`, `helpful`, `terminal_state`, `outcome_ref`, `idempotency_key` | The evidence ID must be from that exact receipt; terminal state is `succeeded`, `failed`, `interrupted`, or `retry`; outcome is a verified opaque reference. |

The current SDK convention is generated from `surface.json`; regenerate all
language surfaces and documentation with the normal SDK rollout gate. A local
type is not a substitute for a released SDK operation or transport.

## Current status — checked 2026-07-17

| State | Evidence | Status |
|---|---|---|
| Implemented locally | SDK contract commit `3c7ba3770c1d5b7e54a0bb25fe876f8ee6371325` contains all three operations. Remi and Auth Hub companion local commits are `285029aca726e0a1391aa207d9fca5a82b69204b` and `3da7aca5f79edaff6d52b27e889d3b68d07d9be6`. | Yes, local only |
| Locally validated | Earlier focused SDK contract/generation and Rust package tests were run on the local contract branch; rerun the SDK gate on the publication candidate. | Partial, release gate still required |
| Remotely published / consumable | SDK `origin/main` is `87d54d3`; its Remi operation table has the legacy operations and does **not** contain `context`, `recordObservation`, or `feedback`. No remote branch contains `3c7ba3770c1d5b7e54a0bb25fe876f8ee6371325`. | No |
| Live end-to-end verified | No versioned generated SDK dependency is available to bind, so no authenticated workflow-to-Remi E2E can truthfully be claimed. | No |

The companion work is likewise not a release proof: Remi `origin/main` does
not contain its local lifecycle commit, and Auth Hub `origin/main` still
advertises `remi_*` and `REMI_MCP_URL`. Those must be reconciled through their
owners' normal reviews; this SDK documentation change does not alter them.

## Binding checklist for Tempera Code

Only start runtime binding after the SDK contract has an approved remote
revision or released package that contains all three operations.

1. Pin that immutable version or commit through the normal dependency policy;
   do not add a path dependency or handwritten HTTP client.
2. Map the pre-plan request exactly to the generated `context` body:
   `question`, optional `max_tokens`, and optional `modes`. The current local
   adapter's `require_fresh` and `reconstruction_mode` fields are **not** in
   the generated SDK contract and must be removed from the wire mapping or
   deliberately added, generated, reviewed, and released before use.
3. On unavailable, invalid, timed-out, or cancelled context, continue with no
   memory. Retain the returned receipt ID and evidence IDs only in workflow
   state needed for receipt-bound feedback.
4. Enqueue lifecycle observations atomically with workflow events. Use the
   journal-derived idempotency key and only bounded redacted summaries plus
   opaque artifact/checkpoint/trace references.
5. Let the app-server-owned maintenance worker lease a bounded batch, deliver
   through the SDK, record a delivery/retry audit event, and use bounded
   exponential backoff. It must not be an arbitrary cron or tool runner.
6. On cancellation, cancel outstanding outbox work and never report it as
   success. Send feedback only with a retained exact receipt/evidence pair,
   a verified outcome reference, and one of the four terminal states above.
7. Instrument context fallback, receipt rejection, outbox lease/delivery/retry
   /cancellation counts, and delivery latency. Do not emit raw lifecycle
   content in metrics or logs.

## Release gate and smallest safe next step

The blocking gate is publication: land the reviewed Remi and Auth Hub
contract changes, land/regenerate the SDK surface, pass the SDK's full
`npm test` contract gate, and publish or otherwise approve a portable SDK
revision. Then the Tempera Code owner can pin that exact release and run one
authenticated SDK-shaped E2E covering context, durable observation delivery,
checkpoint identity, receipt-bound terminal feedback, retry, and cancellation.

Until then, do not fabricate delivery by marking outbox rows complete, and do
not replace the SDK transport with direct HTTP.
