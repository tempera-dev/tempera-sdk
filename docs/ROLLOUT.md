# Endpoint-change rollout: how the SDK stays in sync with the products

The Tempera SDK exposes one uniform surface in three languages. Uniformity is
not a convention — it is generated and gated. This document is the contract
for what happens when any product endpoint changes.

## The chain of custody

```
product handler change                     (palette, tempo, cradle, remi, data-engine, auth-hub)
  └─ product contract artifact             (each repo's own gate, see table below)
       └─ surface.json in this repo        (single source of truth for the SDK)
            └─ scripts/gen-sdk-surface.py  (renders the per-language tables)
                 ├─ packages/typescript/src/surface.js + surface.d.ts
                 ├─ packages/python/src/tempera_sdk/surface.py
                 └─ packages/rust/src/surface.rs
                      └─ scripts/check-sdk-surface.py + per-language tests (CI)
```

Every product repo already gates its own contract; the SDK pins to those
artifacts:

| Product | Contract artifact | Product-side gate |
|---|---|---|
| auth-hub | `contracts/control-plane.openapi.json` | `scripts/check-control-plane-openapi.py` |
| palette | `sdks/openapi/palette-api.json` (generated from `#[utoipa::path]`) | `scripts/check-contract-sync.sh` (CI: sdk-contract.yml) |
| cradle | `sdks/openapi.json` (utoipa, committed) | `tests/openapi_drift.rs` + `tests/mcp_catalog_drift.rs` |
| tempo | `GET /openapi.json` (runtime-generated; no committed snapshot yet) | route/spec coverage tests in `tempo-headless` |
| remi | axum router in `crates/remi/src/server.rs` (no spec) | `cargo test -p remi` |
| data-engine | `api/openapi.yaml` (contract-first, committed) | route/auth coverage in `tests/test_mvp.py` |

## When a product endpoint changes

1. **Land the product change** behind its own contract gate (regenerate the
   product's OpenAPI/catalog artifacts as that repo requires).
2. **Update `surface.json`** in this repo: add/adjust the operation entry
   (id, method, path, params, auth kind, scope, one-sentence description).
   - Adding an endpoint or an optional parameter → **minor** SDK version bump.
   - Renaming/removing an operation, changing a path, method, auth kind, or
     the error contract → **major** bump (pre-1.0: bump the minor and call it
     out in the PR).
   - Until the tables are updated, callers are not stranded: undeclared
     parameters pass through (query on GET/DELETE, body otherwise) and every
     product client has a raw `request(path, ...)` escape hatch.
3. **Regenerate**: `python3 scripts/gen-sdk-surface.py && python3 scripts/gen-sdk-docs.py`
   and commit the four generated surface files **and** the regenerated docs
   site (`docs/site/`) together with `surface.json`. The Mintlify docs are
   generated from the same manifest (and from this file), so a surface change
   that skips the docs regen fails the gate.
4. **Bump all three package versions together** (`packages/typescript/package.json`,
   `packages/python/pyproject.toml`, `packages/rust/Cargo.toml`) — the gate
   fails if they differ.
5. **Run the full gate**: `npm test` at the repo root. That runs, in order:
   - `scripts/check-sdk-surface.py`: surface.json invariants, regenerate-and-
     diff drift check (surface tables **and** the generated docs site),
     version-uniformity check, uniform-primitive markers.
   - TypeScript, Python, and Rust test suites — each contains a conformance
     loop that exercises **every** operation in the generated tables against
     a mock transport (method, substituted path, auth header, body defaults),
     so a table change that the client code cannot serve fails in all three
     languages at once.
6. **Ship** the SDK PR. CI (`.github/workflows/test.yml`) repeats the same
   gates; a PR that edits `surface.json` without regenerating, or regenerates
   without updating tests, cannot merge.

## Error-contract changes

The seven products speak four different wire error shapes (see
`errorContract.wireShapes` in `surface.json`). The SDK normalizes them into
one `TemperaApiError` (`status`, `code`, `message`, `requestId`, `product`,
`operation`, `body`, plus the retry metadata `retryable`/`retryAfter`) in
every language. If a product changes its error shape:

1. Update `errorContract` in `surface.json` (the shapes are documentation,
   but keep them exact).
2. Update `normalizeErrorBody` / `normalize_error_body` in all three packages
   and their shape tests (each package tests every wire shape).

A product adding a *new* shape should prefer one of the existing ones —
ideally the cradle shape (`{"error": {code, message, request_id, ...}}`),
which is the richest. tempera-gym follows it with
`{"error": {code, message, retryable}}`.

Backends that emit `retryable` feed the SDK's opt-in bounded retry: the
TypeScript (`createTemperaClient({retry})`) and Python
(`TemperaClient(retry=...)`) clients retry idempotent (GET/DELETE) requests
whose normalized error is retryable — the server-declared flag when present,
else HTTP 429/502/503/504 — with capped exponential backoff honoring a
numeric `Retry-After` header; default OFF. The HTTP-less Rust crate exposes
the same signal as `TemperaApiError::retryable` / `is_retryable()` for the
caller's own transport loop.

## Adding a product

1. Add the product to `products` in `surface.json` (key, repo, `TEMPERA_*_URL`
   env var, audience or `null`, one-sentence description). Products without
   typed operations still get a passthrough client in all three languages.
2. If it has a registered audience, confirm the audience exists in auth-hub's
   `TEMPERA_RESOURCE_AUDIENCES` first — the SDK's audience list must stay a
   subset of the control plane's.
3. Add typed operations when its HTTP contract is stable; regenerate; test.

## Keeping the fleet honest

- The SDK's audiences/scopes lists mirror auth-hub's `server.js` registries;
  auth-hub CI runs `scripts/check-auth-control-plane.py` against its docs and
  the SDK repo checks the lists in `test/sdk.test.mjs` (and the Python/Rust
  equivalents) so a control-plane registry change breaks the SDK gate loudly.
- Palette's committed OpenAPI is the reference for palette operation paths;
  when palette CI regenerates its spec, any path change that affects a
  `surface.json` operation must land here in the same rollout.
