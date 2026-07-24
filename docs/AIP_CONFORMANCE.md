# Google Cloud AIP conformance

The aggregate SDK treats committed producer contracts as authoritative and
applies the Google Cloud API Improvement Proposals to ordinary HTTP resource
APIs. This is a migration ratchet, not a blanket compliance claim.

## Enforced now

`python3 scripts/check-aip-conformance.py` examines every exact-vendored
producer contract and fails when:

- an unreviewed resource route lives outside `/v1`;
- an ordinary resource method uses `PUT`;
- path or query parameters are not lowerCamelCase;
- JSON request or response fields reachable from an ordinary resource method
  are not lowerCamelCase;
- a colon custom verb is not lowerCamelCase;
- a List method omits `pageSize` or `pageToken`;
- a PATCH method omits `updateMask`;
- an ordinary resource operation omits a `google.rpc.Status`-compatible JSON
  error envelope with numeric `error.code`, string `error.status` and
  `error.message`, and array `error.details`;
- a recorded violation disappears without removing its stale exception; or
- the baseline review date expires.

Data Engine additionally publishes `x-tempera-resource-pattern: projects/*`
for its `parent` parameter. TypeScript, Python, and Rust expand that resource
name as path segments, validate its literal prefix and wildcard count, reject
dot segments, and encode wildcard content without encoding the canonical `/`.

The exact legacy snapshot is
`contracts/aip-conformance-baseline.json`. Updating it is a reviewed migration
operation:

```sh
python3 scripts/check-aip-conformance.py --update-baseline
python3 scripts/check-aip-conformance.py
```

CI never invokes `--update-baseline`.

## Breaking producer migrations

The remaining work must land producer-first and then regenerate the SDK from
the producer's immutable merge SHA:

1. Adopt canonical `name` and `parent` resource names and standard
   Get/List/Create/Update/Delete request shapes (AIP-122 and AIP-131–135).
2. Replace legacy action paths with lowerCamel colon custom methods where a
   standard method does not apply (AIP-136).
3. Add opaque, request-bound pagination to every List method (AIP-158).
4. Replace copied terminal `Operation` envelopes with a pollable Operations
   service for genuinely long-running work (AIP-151).
5. Add `requestId` only where the producer durably guarantees replay-safe
   idempotency (AIP-155).
6. Use `updateMask` for partial updates (AIP-161).
7. Converge HTTP failures on `google.rpc.Status` JSON semantics: numeric
   `code`, enum-string `status`, `message`, and repeated typed `details`
   (AIP-193).

This order avoids cosmetic renames that leave runtime behavior non-conformant.

## Protocol boundaries

MCP/JSON-RPC, OAuth form and redirect routes, OTLP collectors, inbound
webhooks, WebSocket/BiDi, SSE, well-known metadata, health, readiness, and
metrics endpoints retain their native protocol semantics. Their exact paths
are recorded in the baseline and do not authorize new resource-API exceptions.

Reference policy:

- <https://google.aip.dev/122>
- <https://google.aip.dev/127>
- <https://google.aip.dev/151>
- <https://google.aip.dev/155>
- <https://google.aip.dev/158>
- <https://google.aip.dev/161>
- <https://google.aip.dev/193>
