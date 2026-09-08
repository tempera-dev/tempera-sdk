---
name: tempera-aip-sdk-contract
description: The one HTTP contract every Tempera producer publishes — the canonical contracts/openapi path, Google AIP resource style, the google.rpc.Status envelope, the x-tempera-* extensions, and the vendored linter that enforces all of it with the same rule engine tempera-sdk runs. Use when adding or changing a route, editing an OpenAPI or JSON Schema file, defining a scope or audience, fixing an AIP or drift gate failure, running the producer contract lint, or wiring a repo into the aggregate SDK.
---

# Tempera AIP + SDK contract

Every Tempera product that speaks HTTP publishes **one** machine-readable
contract, in one place, in one format. `tempera-sdk` generates typed
TypeScript, Python, and Rust clients from it; `tempera-mcp` exposes it as
capability cards; `tempera-workflows` calls it from bounded DAGs. Those three
consumers cannot be uniform unless the producers are, so the rules below are
not style preferences — they are what makes a route reachable from the SDK,
MCP, and Workflows at all.

The normative text is `tempera-sdk/docs/CONTRACT_STANDARD.md`. This skill is
how you comply with it from inside a producer repository.

**The producer is the source of truth. Never edit a consumer to describe a
route the producer does not publish.** `tempera-sdk/surface.json` is generated;
hand-editing it is drift, and `check-upstream-drift.py` fails on it in both
directions — phantom operations *and* missing eligible operations.

## 1. Run the linter before you push

The linter is vendored into this repository by the agent kit, so a producer
never reaches into another repository to find out whether it is correct:

```sh
python3 .tempera/agent-kit/scripts/lint_producer_contract.py \
  --product <sdkProductKey> \
  --audience <registered-audience> \
  contracts/openapi/<product>.openapi.json
```

`--audience` is only needed when some operation uses `oauthResource`; repeat it
for several. `--baseline contracts/aip-baseline.json` points at an expiring,
reviewed ledger of violations not yet migrated (§6).

Three files arrive together and belong to each other:

| Vendored path | What it is |
| --- | --- |
| `.tempera/agent-kit/scripts/aip_rules.py` | the rule engine |
| `.tempera/agent-kit/scripts/lint_producer_contract.py` | the producer entry point |
| `.tempera/agent-kit/contracts/status-component.json` | the canonical error envelope |

**They are byte-identical copies of `tempera-sdk/scripts/aip_rules.py`,
`tempera-sdk/scripts/lint_producer_contract.py`, and
`tempera-sdk/contracts/status-component.json`.** Do not edit them here. The
linter locates `aip_rules` in its own directory and `status-component.json` in
a sibling `contracts/`, so the layout is load-bearing; move either and the
linter dies on the first contract it is handed.

Wire it into CI as its own job so a contract change cannot merge unlinted:

```yaml
  contract:
    name: Producer contract standard
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5
        with:
          python-version: "3.12"
      - name: Lint the producer contract
        run: |
          python3 .tempera/agent-kit/scripts/lint_producer_contract.py \
            --product temperaConnectors \
            --audience tempera-connectors \
            contracts/openapi/connectors.openapi.json
```

`tempera-connectors` is the worked example: canonical path, vendored linter,
dedicated CI job.

### One rule engine, two call sites

`aip_rules.py` holds the Google AIP rules and **nothing product-specific**.
Exemptions are passed in as an argument rather than hardcoded:

- `tempera-sdk/scripts/check-aip-conformance.py` runs it over the aggregate
  vendored surface, supplying the SDK's reviewed baseline tables.
- `tempera-sdk/scripts/lint_producer_contract.py` runs it over a single
  producer's contract in the producer's own repository, supplying that
  document's own `x-tempera-protocol-routes`.

That is the entire point: **a contract that passes in its home repository
cannot fail once it is vendored.** When the two copies drift, that guarantee is
gone and a producer gets a green build for a contract the SDK will reject — so
a divergent copy is worse than no copy at all. `auth-hub`'s
`agent-kit/tools/check-vendored-sdk-sources.py` gates the kit's copy against
recorded SHA-256 digests and against the SDK checkout when one is reachable;
`agent-kit/vendored-sdk-sources.json` records the exact upstream commit and
blob SHA of each file.

To change a rule: change it in `tempera-sdk`, land it there, then re-vendor
with `python3 agent-kit/tools/check-vendored-sdk-sources.py --update
--sdk-root ../tempera-sdk` in `auth-hub` and fan the kit out again.

## 2. One file, one path, one format

| Property | Required value |
| --- | --- |
| Path | `contracts/openapi/<product>.openapi.json` |
| `<product>` | repository name without the `tempera-` prefix, kebab-case |
| Format | OpenAPI **3.1.0**, JSON |
| Serialization | `json.dumps(document, indent=2, ensure_ascii=False)` + one trailing newline |
| Key order | whatever your builder emits; the linter never reorders |

`openapi` must be exactly `"3.1.0"`. 3.0.x is upgraded, not tolerated: 3.1.0 is
the first release whose schema dialect is JSON Schema 2020-12, which every
downstream generator already assumes.

Every operation needs a stable `operationId` — it is the SDK method identity
and the MCP capability identity, and renaming one is a breaking change.
JSON Schema components are local `$ref`s inside the same document, or files the
vendoring step inlines; remote `$ref`s are not supported. Every
`#/components/...` pointer must resolve — the linter reports
`unresolved local reference` otherwise, because a contract naming a component
it does not define cannot become a typed operation at all.

**Never hand-edit a generated contract.** If the file is emitted from server
code, edit the handlers and regenerate; the edit you make by hand is erased by
the next regeneration, or worse, survives and describes a route the server does
not serve. Publish `scripts/regen-contract.sh --check`, which exits non-zero
when the committed file does not match the running service. A hand-written
contract needs a drift gate comparing it to the routes actually served.

`references/producer-contract.md` lists where every producer's contract lives
today and who has a real gate.

## 3. Errors are `google.rpc.Status`, everywhere

Every non-2xx response in every operation references the shared component:

```json
{"$ref": "#/components/responses/Error"}
```

`components.responses.Error` and `components.schemas.Status` are **byte-identical
across all producers**; the linter compares yours to
`.tempera/agent-kit/contracts/status-component.json` and fails on any
difference, including a cosmetic one. Copy that file's `schemas.Status` and
`responses.Error` into your document verbatim. The wire body is:

```json
{
  "error": {
    "code": 400,
    "status": "INVALID_ARGUMENT",
    "message": "Human readable, safe to show a developer.",
    "details": []
  }
}
```

`code` is the integer HTTP status, `status` the canonical AIP-193 enum name,
`message` a string, `details` a possibly-empty array. No producer may add a
sibling of `error`, and no producer may return a bare `{"detail": …}` or
`{"message": …}` envelope. The SDK's error normalizer reads exactly those four
fields in all three languages; anything else surfaces as an untyped transport
failure.

## 4. The AIP rules, and the protocol-route discipline

The eight mechanical rules are in
[references/aip-rules.md](references/aip-rules.md) with the exact test and fix
for each: `aip-127-versioned-path`, `aip-127-no-put`,
`aip-127-lower-camel-parameters`, `aip-127-lower-camel-json-fields`,
`aip-136-lower-camel-custom-verb`, `aip-158-list-pagination`,
`aip-161-update-mask`, `aip-193-standard-errors`.

There is no backward-compatibility exemption. These APIs have no external
consumers, so a rename is a rename.

Health and transport routes keep their native semantics and are exempt from the
path and error rules — but **only if you declare them**, at the document root:

```json
"x-tempera-protocol-routes": ["/healthz", "/readyz", "/mcp"]
```

Three properties make this honest rather than a dumping ground:

- **An undeclared route gets no exemption.** The linter does not infer intent
  from a path that merely looks like a health check. If it is not in the list
  it is a resource API and answers to AIP, which means an exemption is always
  a visible, reviewable line in the contract rather than a silent skip.
- **A declared route that does not exist is an error.** Exemptions cannot rot
  in place after the route they covered was deleted, and nobody can pre-declare
  a wildcard for routes they have not written yet.
- **Only genuinely protocol-shaped paths may be declared.** The linter's
  `EXEMPTIBLE` pattern accepts `/healthz`, `/readyz`, `/livez`, `/metrics`,
  `/mcp`, `/bidi`, `/openapi.json`, `/.well-known/*`, `/oauth/*`,
  `/v1/otlp/*`, `/v1/webhooks/*`, and paths ending `webhook`, `/callback`, or
  `/events`. Declaring `/v1/orders` a protocol route is refused outright.

Declaring a route exempt is not free — it takes that route out of the typed
SDK surface. Exempt what genuinely speaks another protocol, and nothing else.

Beyond the mechanical gate, resource design follows AIP-122 and AIP-131–135:
canonical `name`/`parent` resource names rather than ID tuples, lowerCamel
plural collections, standard Get/List/Create/Update/Delete shapes, and colon
custom methods (AIP-136) where no standard method applies.

## 5. Declare auth, scope, and effect on every operation

The SDK reads these OpenAPI extensions; anything you do not declare, it cannot
generate. The linter requires them on every non-exempt operation.

| Extension | Type | Meaning |
| --- | --- | --- |
| `x-tempera-auth-kind` | `none` \| `account` \| `product` \| `oauthResource` \| `introspectionSecret` | which credential the SDK attaches. Required on every operation. |
| `x-tempera-auth-audience` | string | the RFC 8707 resource audience. Required exactly when `auth-kind` is `oauthResource`, and **rejected** on any other kind. Must be registered. |
| `x-tempera-required-scope` | string | the single scope the route demands. Required unless `auth-kind` is `none`, and **rejected** when it is `none` — an unauthenticated route cannot require a scope. |
| `x-tempera-physical-action` | boolean | the call has an effect outside the database: money moves, a message is sent, hardware actuates. |
| `x-tempera-prepare-commit-required` | boolean | that effect is only reachable through prepare/commit. Implies `physical-action`, and the linter rejects it without one. |
| `x-tempera-resource-pattern` | object | the AIP-122 pattern for a path parameter, e.g. `{"parent": "projects/*"}`. Required on operations addressing a resource by name. |

Never invent a scope downstream. Register it in the control plane and in
`surface.json`'s `scopes`, or record it under `scopeGaps` with an owner.

## 6. Never re-baseline to turn a build green

A baseline is an expiring, reviewed ledger of violations a producer has not
migrated yet — `--baseline contracts/aip-baseline.json` locally, and
`tempera-sdk/contracts/aip-conformance-baseline.json` for the aggregate. It
records debt; it does not forgive it.

It is symmetric on purpose: a baseline entry whose violation you **fixed**
without removing the entry also fails, so the ledger cannot quietly overstate
what is broken. And `review_after` expires, so a violation cannot be parked
indefinitely without a named owner looking at it again.

**Adding a violation to a baseline in order to make a red build green is how
debt becomes permanent.** Fix the producer, then re-baseline to *remove* the
entry. `--update-baseline` on the SDK's gate is a reviewed migration operation
and is never run in CI.

## 7. Propagation is automatic

Nobody copies a spec between repositories.

1. You merge a contract change to `main` in the producer.
2. `.github/workflows/notify-sdk.yml` — one identical file the agent kit
   installs in every producer — fires a `repository_dispatch` of type
   `tempera-contract-updated` at `tempera-dev/tempera-sdk` with
   `{"product": "<sdkKey>", "commit": "<sha>"}`.
3. The SDK's `.github/workflows/contract-updated.yml` receives it, validates
   the payload against its committed registry (an unknown product or a non-SHA
   commit stops before any checkout or token mint), and runs
   `scripts/revendor-product.py`. That is the whole producer-to-SDK chain in
   one command — vendor at the exact commit, write the `.source` lock,
   regenerate `surface.json`, regenerate all three language surfaces,
   regenerate the docs — in an order that is not optional, because running the
   steps by hand in the wrong order used to leave a `surface.json` no committed
   spec produced.
4. The SDK runs its gates and opens a pull request.

Doing it by hand is the same command: `python3 scripts/revendor-product.py
--products <key> --commit <sha>` from `tempera-sdk`.

### The dispatch is not live yet — the one-time administrator action

**Today no producer can actually send that dispatch.** Firing a
`repository_dispatch` needs a token with write access to
`tempera-dev/tempera-sdk`, and the only GitHub App installed org-wide,
`tempera-contract-reader`, is **read-only by design**.

So `notify-sdk.yml` ships with its mint step referencing organization secrets
that do not exist yet, and a preflight step that **skips the job with an
explanation** when they are absent. It does not fail. A missing org secret must
not turn into a red build on every producer in the organization.

Propagation still happens meanwhile: `contract-updated.yml` also runs on a
three-hourly schedule and re-vendors every producer from `main`, so today a
contract change reaches the SDK within three hours instead of within seconds.

To make it immediate, an organization administrator does this **once**:

1. Create a GitHub App in the `tempera-dev` organization — suggested name
   `tempera-contract-notifier`.
2. Give it exactly one repository permission: **Contents: Read and write**.
   That is the permission `POST /repos/{owner}/{repo}/dispatches` requires.
   Nothing else.
3. Install it in `tempera-dev` and scope the installation to
   **`tempera-sdk` only**. Every producer will hold a credential that can write
   to it, so it must not reach any other repository.
4. Generate a private key (PEM).
5. Add two **organization** secrets, visible to all repositories:
   - `TEMPERA_CONTRACT_NOTIFIER_CLIENT_ID` — the app's client id
   - `TEMPERA_CONTRACT_NOTIFIER_PRIVATE_KEY` — the PEM contents

No producer repository changes. Every repo that already has `notify-sdk.yml`
becomes immediate on its next contract push.

One detail: the workflow derives the SDK product key from the repository name
in camel case (`tempera-connectors` → `temperaConnectors`, `data-engine` →
`dataEngine`), which is why one identical file works everywhere. A repository
whose SDK key does not follow from its name sets the repository variable
`TEMPERA_SDK_PRODUCT_KEY` — `auth-hub` publishes as `controlPlane` and needs
it.

## 8. Entering the SDK

A product becomes SDK-visible by being added, in the same change, to:

- `PRODUCTS` in `tempera-sdk/scripts/sync-vendored-openapi.py` (the vendoring
  registry, and the single registry of record — `revendor-product.py`,
  `resolve-contract-dispatch.py`, and the CI matrix all read it)
- `PRODUCT_SPECS` and `DEFAULT_AUTH` in `scripts/sync-openapi-surface.py`
- `SPECS` in `scripts/check-aip-conformance.py` and `check-upstream-drift.py`
- `products` in `surface.json`

Miss the `SPECS` entry and the product's routes silently skip the AIP gate;
`check_specs_cover_surface()` now fails the build when that happens, so add
them all together.

Exact-source verification is no longer something to remember separately. The
matrix in `tempera-sdk/.github/workflows/test.yml` is **generated** from the
vendoring registry by `scripts/gen-exact-source-matrix.py`, so a product exists
in the registry or it is not vendored at all — omission is impossible rather
than merely discouraged. Consequently
`tempera-sdk/contracts/sdk-exact-source-gaps.json` is empty by design, and
`check-exact-source-gaps.py` **refuses** a gap for any repository the matrix
already covers: such a gap is not a blocker, it is stale paperwork hiding the
fact that verification is already running.

## 9. Downstream consumers

- **MCP.** `tempera-mcp` exposes ten fixed `tempera_*` fabric verbs; product
  capabilities are opaque policy-filtered cards, never flat product tool names.
  An upstream is added in `deploy/tempera.toml` with an `admission_contract`
  and a runtime-derived catalog lock pinned to an exact producer commit. The
  gateway speaks the stateless MCP `2026-07-28` discovery lifecycle
  (`server/discover`, not `initialize`); `surface.json`'s `mcpGateway` block
  and the three SDK MCP clients must agree with the server.
- **Workflows.** `tempera-workflows` calls products through its node catalog.
  A contract change reaches it as a fixture handoff pinned to the producer SHA,
  not by editing active studio paths.
- Add an MCP capability only for deliberately model-facing operations, and
  record its effect class and required scopes from the authoritative registry.

## 10. Fail closed

Do not call it done if:

- the linter did not run, or ran on a different file than the one you committed;
- a violation was baselined rather than fixed, to make a build green;
- a generated contract was hand-edited;
- a route was declared in `x-tempera-protocol-routes` to dodge a rule rather
  than because it speaks another protocol;
- the vendored `.tempera/agent-kit/scripts/*` differ from `tempera-sdk`'s;
- the producer tree was dirty when it was vendored, or provenance cannot be
  reproduced with `git show <commit>:<path>`;
- drift was checked in only one direction;
- a scope was invented downstream;
- the three language surfaces differ, or `surface.json` was hand-edited;
- CI never ran the gates on a runner.
