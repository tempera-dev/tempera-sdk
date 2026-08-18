# Five-language SDK contract

Tempera exposes one versioned API contract through TypeScript, Python, Rust, Go, and C. `surface.json` is the language-neutral SDK manifest; producer OpenAPI remains authoritative for HTTP routes, methods, request fields, auth annotations, and operation identity.

## Language responsibilities

| Language | Package | Transport model | BrowserTask |
|---|---|---|---|
| TypeScript | `packages/typescript` | built-in `fetch` | executing loop + workflow |
| Python | `packages/python` | configured SDK transport | executing loop + workflow |
| Rust | `packages/rust` | HTTP-less `RequestSpec` builder | transport-neutral request builder |
| Go | `packages/go` | standard-library `net/http` | executing loop + workflow |
| C | `packages/c` | HTTP-less caller-owned transport | transport-neutral request builder |

Rust and C intentionally do not select an HTTP/TLS implementation for the caller. This keeps those packages usable in embedded, sandboxed, FFI, and custom-runtime deployments without imposing a networking dependency. Go uses only the standard library.

## Contract flow

```text
producer repository
  -> committed OpenAPI / protocol contract
  -> exact-source lock in tempera-sdk
  -> vendored specs/*
  -> surface.json
  -> generated TypeScript / Python / Rust surfaces
  -> generated Go / C surfaces
  -> language-specific ergonomic layers such as BrowserTask
```

A staged producer PR may be tested by an SDK PR, but a release lock must point to an immutable approved producer revision under the repository's exact-source policy. A staged branch is not silently promoted to a release source.

## Uniformity invariants

All five packages must ship the same semantic SDK version. Every generated product operation must preserve the producer method, path, auth kind/audience, scope, required query/body fields, path-resource templates, request-body kind, and producer operation ID. Language-idiomatic method naming may differ, but wire field names and HTTP semantics may not.

The repository's Google Cloud AIP ratchet remains producer-first. It currently checks versioned resource paths, lower-camel parameter and JSON field names, custom verbs, list pagination, update masks, standard error envelopes, and the prohibition on newly introduced `PUT` routes. Protocol-native OAuth, MCP, OTLP, webhook, WebSocket/BiDi, and SSE routes remain explicit exceptions rather than being mechanically rewritten into REST resources.

## Errors

HTTP SDKs normalize server failures into the same conceptual shape: HTTP status, canonical code/status when present, message, request ID, product, operation, and original response body. Canonical AIP-193 `error` envelopes take precedence; compatibility parsing exists only for producer contracts that have not yet completed their migration.

## BrowserTask

`BrowserTask` is an ergonomic layer over generated Tempo operations, not a second browser protocol. It owns or attaches to one Tempo session, exposes observation/action/close primitives, supports a bounded agent loop where the language has an execution runtime, and reuses authoritative settled observations when Tempo returns them. Rust and C expose request-building lifecycle helpers instead of adding an HTTP runtime.

## Release gates

A releasable SDK revision requires:

1. producer contracts and exact-source provenance are valid;
2. `surface.json` is regenerated from those contracts;
3. generated TypeScript/Python/Rust and Go/C surfaces have zero drift;
4. the AIP conformance ratchet passes;
5. all five language package tests pass at the same version;
6. generated docs are current;
7. known exact-source installation gaps remain fail-closed until actually resolved rather than being waived by date changes.
