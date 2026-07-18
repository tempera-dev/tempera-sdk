# Remi and Tempera Code integration readiness

This is a release-readiness checklist for the durable Remi lifecycle path. It
describes the contract candidate; it is not evidence that an authenticated
runtime integration has been published or verified live.

## Ownership and transport

Tempera Code owns workflow dispatch, its durable journal/outbox, cancellation,
and bounded maintenance scheduling. The generated SDK owns portable operation
names, request shapes, and authentication transport. Remi derives memory scope
from the authenticated principal and owns retrieval receipts, evidence
validation, feedback acceptance, and ledger truth.

Do not bind Tempera Code with a path dependency or handwritten HTTP. Pin an
approved immutable SDK revision/package after this candidate has passed review
and publication gates.

## Required generated operations

| Operation | Contract |
|---|---|
| `context` | `POST /v1/context`; `question` plus bounded retrieval controls. Do not send scope, tenant, project, or environment identifiers. Retain only the returned receipt and evidence IDs required for feedback. |
| `remember` | `POST /v1/remember`; `kind`, redacted `text`, idempotency key, and bounded `remi.memory_event_provenance.v1` correlation metadata with opaque artifact references. Never send prompts, tool bodies, patches, command output, secrets, or browser content. |
| `feedback` | `POST /v1/feedback`; use `remi.memory_feedback.v2` with exact `retrieval_receipt_id`, `evidence_node_id`, `helpful`, canonical `outcome_artifact_id`, `terminal_state` (`succeeded`, `failed`, `interrupted`, or `retry`), and an idempotency key. |

Same-key replay is expected to be idempotent; changed payload under the same
key must conflict. Workflow code currently using `outcome_ref` must map it to
the canonical `outcome_artifact_id` before calling the generated feedback
operation.

## Binding checklist

1. Pin the reviewed SDK version; regenerate all language surfaces from
   `surface.json` and run the SDK contract gate first.
2. On unavailable, invalid, timed-out, or cancelled context, continue without
   memory; do not fabricate a receipt.
3. Enqueue redacted lifecycle observations atomically with workflow events and
   deliver `remember` with journal-derived idempotency keys.
4. Send feedback only for the retained exact receipt/evidence pair and a
   verified opaque outcome artifact reference.
5. Instrument fallback, receipt rejection, outbox delivery/retry/cancellation,
   and delivery latency without raw lifecycle content.

The remaining runtime gate is an authenticated SDK-shaped E2E covering context,
durable remember delivery, receipt-bound V2 feedback, retry, and cancellation.
