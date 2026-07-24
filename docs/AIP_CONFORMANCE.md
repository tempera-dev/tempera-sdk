# Google Cloud AIP conformance

The aggregate SDK treats committed producer contracts as authoritative and
applies the Google Cloud API Improvement Proposals to ordinary HTTP resource
APIs. This is a migration ratchet, not a blanket compliance claim.

The distinction is intentional: a zero count in the executable checks below
means the versioning, wire casing, custom-verb casing, pagination, update-mask,
and error-envelope rules are clean. It does not by itself prove that every
domain has completed the breaking AIP-122 and AIP-131–135 resource-model
migration.

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

### Current structural inventory

The following producer-owned work remains after the mechanical gate. It is
recorded here so a green aggregate build cannot be presented as blanket Google
API compliance.

| Producer | AIP-122 and standard-method migration |
|---|---|
| Auth Hub | Replace ID tuples with canonical resource names, remove kebab-case collections, and give management-plane Create/Update/Delete families standard resource shapes. |
| Cradle | Make Module and Job routes use canonical `name`/`parent`; add missing List methods or classify command execution as a custom method rather than Job creation. |
| Data Engine | Finish canonical names beyond its Discovery Release, Evidence Record, and Episode families; replace split parent-plus-ID item routes and standardize Create/Delete bodies. |
| Palette | Replace tenant/project/resource ID tuples with canonical names and complete the currently create/list/get-only resource families. |
| Tempera Gym | Document canonical names, use them in Gets, return created resources directly, and model rollout execution as an explicit custom or long-running method. |
| Tempera Workflows | Separate display names from canonical names, use `name`/`parent`, make `updateMask` optional, and replace `/node-types` with a lower-camel collection. |
| Tempo | Give Session and Run canonical names, use `name`/`parent`, and return the created Session resource. |
| Remi | Model remember/project/query/maintenance as explicit colon custom methods or introduce standard resource families. |

Tempera LLM remains an exact OpenAI-compatible protocol surface. Bio's sealed
artifact pipeline uses explicit colon custom methods rather than pretending its
derivations are CRUD resources. Human Data's qualification receipt is governed
by its committed producer contract. These decisions do not waive the mechanical
wire and error rules.

## Protocol boundaries

MCP/JSON-RPC, OAuth form and redirect routes, OTLP collectors, inbound
webhooks, WebSocket/BiDi, SSE, well-known metadata, health, readiness, and
metrics endpoints retain their native protocol semantics. Tempera LLM's
`/v1/chat/completions`, `/v1/responses`, and `/v1/models` routes likewise
retain the OpenAI-compatible JSON field names required by existing clients.
OAuth introspection retains the RFC 7662 wire contract even at its exact
versioned Auth Hub operation. Auth Hub's session, workspace-selection,
staff-step-up, and OAuth-grant management operations retain embedded OAuth
token/grant response vocabulary while their resource paths, parameters,
pagination, and AIP-193 errors remain governed by the resource rules.

Exact path, operation, and JSON-only exceptions are recorded separately in the
baseline. This prevents a protocol response from exempting unrelated methods or
other AIP rules and does not authorize new resource-API exceptions.

Reference policy:

- <https://google.aip.dev/122>
- <https://google.aip.dev/127>
- <https://google.aip.dev/131>
- <https://google.aip.dev/132>
- <https://google.aip.dev/133>
- <https://google.aip.dev/134>
- <https://google.aip.dev/135>
- <https://google.aip.dev/136>
- <https://google.aip.dev/151>
- <https://google.aip.dev/155>
- <https://google.aip.dev/158>
- <https://google.aip.dev/161>
- <https://google.aip.dev/193>
