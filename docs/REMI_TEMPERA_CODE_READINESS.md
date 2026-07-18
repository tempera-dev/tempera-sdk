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
| `context` | `POST /v1/context` | `question` | Optional `max_tokens`, `require_fresh`, `modes`, and bounded reconstruction controls; no client-supplied tenant, project, environment, or workspace scope. Response must carry a retrieval receipt and cited evidence. |
| `remember` | `POST /v1/remember` | `kind`, `text` | Lifecycle writes use an idempotency key and the bounded `remi.memory_event_provenance.v1` envelope (`trace_id`, rollout/turn/tool IDs, producer, and opaque `artifact_refs`). `text` is a redacted summary only; checkpoint identity belongs in an opaque artifact reference. Never send prompts, tool bodies, patch bodies, command output, secrets, or browser content. |
| `feedback` | `POST /v1/feedback` | `schema`, `retrieval_receipt_id`, `evidence_node_id`, `helpful`, `terminal_state`, `outcome_artifact_id`, `idempotency_key` | Use `remi.memory_feedback.v2`. The evidence ID must be from that exact receipt; terminal state is `succeeded`, `failed`, `interrupted`, or `retry`; the outcome artifact is a verified opaque `artifact://`, `test://`, `review://`, or `deploy://` reference. |

The current SDK convention is generated from `surface.json`; regenerate all
language surfaces and documentation with the normal SDK rollout gate. A local
type is not a substitute for a released SDK operation or transport.

## Current status — checked 2026-07-17

| State | Evidence | Status |
|---|---|---|
| Implemented locally | SDK contract commit `6abd466` contains generated `context`, `remember`, and V2 `feedback` operations. Remi and Auth Hub companion local commits are `12deeb9` and `6532439`. | Yes, local only |
| Locally validated | Earlier focused SDK contract/generation and Rust package tests were run on the local contract branch; rerun the SDK gate on the publication candidate. | Partial, release gate still required |
| Remotely published / consumable | SDK `origin/main` is `87d54d3`; its Remi operation table does **not** contain `context` or V2 terminal feedback. No remote branch contains `6abd466`. | No |
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
   `question`, optional `max_tokens`, `require_fresh`, `modes`, and bounded
   reconstruction controls. The existing local adapter's `require_fresh` and
   `reconstruction_mode` fields are generated SDK fields; keep their values
   bounded and covered by the same release.
3. On unavailable, invalid, timed-out, or cancelled context, continue with no
   memory. Retain the returned receipt ID and evidence IDs only in workflow
   state needed for receipt-bound feedback.
4. Enqueue lifecycle memory observations atomically with workflow events. Use
   the journal-derived idempotency key and the generated `remember` body: a
   bounded redacted summary, plus opaque artifact/checkpoint/trace references
   in its provenance envelope.
5. Let the app-server-owned maintenance worker lease a bounded batch, deliver
   `remember` calls through the SDK, record a delivery/retry audit event, and
   use bounded exponential backoff. It must not be an arbitrary cron or tool
   runner.
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
authenticated SDK-shaped E2E covering context, durable `remember` delivery,
checkpoint identity carried as provenance, receipt-bound terminal feedback,
retry, and cancellation.

Until then, do not fabricate delivery by marking outbox rows complete, and do
not replace the SDK transport with direct HTTP.
