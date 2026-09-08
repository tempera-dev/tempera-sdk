# The eight mechanical AIP rules, and how to fix each

These live in **one** implementation, `tempera-sdk/scripts/aip_rules.py`,
vendored into this repository byte-for-byte at
`.tempera/agent-kit/scripts/aip_rules.py`. Two call sites run it:

| Call site | Input | Exemptions it supplies |
| --- | --- | --- |
| `lint_producer_contract.py` | one producer's own contract, in the producer's repo | that document's `x-tempera-protocol-routes` |
| `tempera-sdk/scripts/check-aip-conformance.py` | the aggregate vendored surface | the SDK's reviewed baseline tables |

Because the rules are identical, a contract that passes locally cannot fail
after vendoring. Run it before you push:

```sh
python3 .tempera/agent-kit/scripts/lint_producer_contract.py \
  --product <sdkProductKey> \
  --audience <registered-audience> \
  contracts/openapi/<product>.openapi.json
```

The linter checks the format half of the standard too — OpenAPI 3.1.0,
canonical serialization, byte-identical `google.rpc.Status` components, honest
protocol routes, and the `x-tempera-*` extensions — before it ever reaches the
eight rules below.

It also resolves every `#/components/...` pointer in the document and reports
`unresolved local reference: <pointer>` for any that does not land. A contract
referencing a component it never defines looks fine to a reviewer and fine to
the AIP rules, and then cannot be turned into a typed operation at all;
`tempera-connectors` shipped four of these because utoipa emitted
fully-qualified `crate.models.X` names for bodies registered under their short
names, and nothing caught it until the SDK tried to generate from it.

## aip-127-versioned-path
**Test.** A non-protocol resource route whose path does not start with `/v1`.
**Fix.** Move it under `/v1`. If it is a health, metrics, OAuth, webhook, OTLP,
SSE, WebSocket, or `.well-known` route, declare it in
`x-tempera-protocol-routes` at the document root rather than versioning it —
and see the discipline section below before you do.

## aip-127-no-put
**Test.** `PUT` on an ordinary resource method.
**Fix.** `POST` to the collection creates; `PATCH` with `updateMask` updates.
An idempotent full-replace upsert is a colon custom method (`:upsert`), not
`PUT`. Binary uploads that genuinely need `PUT` are protocol routes.

## aip-127-lower-camel-parameters
**Test.** A path or query parameter name that is not `lowerCamelCase`.
**Fix.** `{document_id}` → `{documentId}`, and preferably → `{name}` carrying a
canonical resource name (AIP-122). Renaming a parameter is breaking; land it
with the producer's own deprecation window.

## aip-127-lower-camel-json-fields
**Test.** A JSON request or response property reachable from an ordinary
resource method that is not `lowerCamelCase`. Resolution follows local `$ref`s
and `allOf`/`anyOf`/`oneOf`.
**Fix.** Rename the field. If the route deliberately implements a foreign wire
contract — OpenAI-compatible, RFC 7662 introspection, OAuth token responses —
that is a protocol route: in the SDK's aggregate gate it belongs in
`protocol_json_exceptions`, which exempts *only* that operation's JSON, not its
paths, parameters, pagination, or errors.

## aip-136-lower-camel-custom-verb
**Test.** The segment after `:` in a custom method is not `lowerCamelCase`.
**Fix.** `:compute_qualification` → `:computeQualification`.

## aip-158-list-pagination
**Test.** A List method that does not accept both `pageSize` and `pageToken`.
**Fix.** Add both, and return `nextPageToken`. The token is opaque and bound to
the original request; do not expose an offset.

## aip-161-update-mask
**Test.** A `PATCH` that does not accept `updateMask`.
**Fix.** Accept `updateMask` and apply only the named fields. An absent mask
means "replace the fields present in the body"; an empty mask is a no-op.

## aip-193-standard-errors
**Test.** Every `4xx`, `5xx`, `4XX`, `5XX`, and `default` response must declare
`application/json` with a schema whose `error` object carries `code` (integer),
`status` (string), `message` (string), and `details` (array). An operation with
no error response at all fails as `missing-error-response`.

**Fix.** Do not write the schema yourself. Copy `schemas.Status` and
`responses.Error` verbatim out of
`.tempera/agent-kit/contracts/status-component.json` into your document's
`components`, and reference it from every error response:

```json
{"$ref": "#/components/responses/Error"}
```

The linter compares your two components to that file and fails on **any**
difference, including a reordered key or a changed description. They are
byte-identical across all producers precisely so the SDK's error normalizer can
read the same four fields in TypeScript, Python, and Rust; anything else
surfaces as an untyped transport failure.

`error.status` is the canonical enum string (`NOT_FOUND`, `INVALID_ARGUMENT`,
`PERMISSION_DENIED`, …), `error.code` the numeric HTTP status, and
`error.details` a list of typed detail objects such as `google.rpc.ErrorInfo`.

## The protocol-route discipline

An exemption is a declaration in your own contract, not something the checker
infers:

```json
"x-tempera-protocol-routes": ["/healthz", "/readyz", "/mcp"]
```

- **An undeclared route gets no exemption.** A path that merely looks like a
  health check is still a resource API. This is what keeps every exemption a
  visible, reviewable line in the contract instead of a silent skip.
- **A declared route that does not exist is an error.** Exemptions cannot rot
  after the route they covered is deleted, and nobody can pre-declare a
  wildcard for routes not yet written.
- **Duplicates are an error.**
- **Only protocol-shaped paths may be declared at all.** The accepted shapes
  are exactly:

  | Shape | Examples |
  | --- | --- |
  | exact | `/healthz`, `/readyz`, `/livez`, `/metrics`, `/mcp`, `/bidi`, `/openapi.json` |
  | prefix | `/.well-known/…`, `/oauth/…`, `/v1/otlp/…`, `/v1/webhooks/…` |
  | suffix | `…webhook`, `…/callback`, `…/events` |

  Anything else — `/v1/orders`, `/internal/reindex` — is refused with
  *"is a resource route and cannot be declared a protocol route"*.

Declaring a route exempt is not free: it takes that route out of the typed SDK
surface, so the SDK cannot generate a client method for it. Exempt what
genuinely speaks another protocol, and nothing else.

## Reviewing the baseline

```sh
# producer-local, expiring, reviewed
python3 .tempera/agent-kit/scripts/lint_producer_contract.py \
  --product <key> --baseline contracts/aip-baseline.json contracts/openapi/<product>.openapi.json

# the SDK's aggregate ledger
python3 scripts/check-aip-conformance.py                    # gate
python3 scripts/check-aip-conformance.py --update-baseline  # reviewed only
```

A producer baseline is a JSON object with `schema_version: 1`, an ISO
`review_after` date, and `accepted_violations`. It fails when the date passes,
so a violation cannot be parked indefinitely without a named owner looking at
it again.

It is deliberately symmetric: a baselined entry whose violation you **fixed**
also fails, with *"baselined but no longer a violation; remove it"*. The ledger
cannot quietly overstate what is broken.

**Re-baselining to make a red build green is how debt becomes permanent.** Fix
the producer, then re-baseline to *remove* the entry. `--update-baseline` is a
reviewed migration operation and is never run in CI.
