# Where each producer's contract lives

The canonical path is `contracts/openapi/<product>.openapi.json`, and most of
the organization is now on it. The tables below are a **snapshot verified
against the working checkouts on 2026-09-07**, during an active migration:
several producers moved to the canonical path that day and their SDK registry
entries have not all caught up.

Treat this as orientation, not as an authority. Two things are authoritative,
and you should read them rather than this file when it matters:

- **`tempera-sdk/scripts/sync-vendored-openapi.py` → `PRODUCTS`** is the single
  registry of record. `revendor-product.py`, `resolve-contract-dispatch.py`,
  and the generated exact-source CI matrix all import it. If a path is wrong
  there, vendoring fails; if a path is wrong here, only this document is wrong.
- **The repository itself.** `ls contracts/openapi/`.

`controlPlane` is not in `PRODUCTS`; `auth-hub` has its own vendoring script,
`tempera-sdk/scripts/sync-control-plane-openapi.py`, pinned to
`contracts/control-plane.openapi.json` on `main`.

## Producers on the canonical path

| Product key | Repository | Contract path | Vendored linter | CI gate |
| --- | --- | --- | --- | --- |
| `temperaConnectors` | tempera-connectors | `contracts/openapi/connectors.openapi.json` | yes | **dedicated `contract` job** |
| `temperaBusiness` | tempera-business | `contracts/openapi/business.openapi.json` | yes | dedicated step in `ci.yml` |
| `temperaDropshipping` | tempera-dropshipping | `contracts/openapi/dropshipping.openapi.json` | yes | dedicated step in `ci.yml` |
| `temperaPayments` | tempera-payments | `contracts/openapi/payments.openapi.json` | yes | via `scripts/regen-contract.sh --check` |
| `temperaRisk` | tempera-risk | `contracts/openapi/risk.openapi.json` | yes | via `scripts/regen-contract.sh --check` |
| `temperaGym` | tempera-gym | `contracts/openapi/gym.openapi.json` | no | repo-local AIP script, not wired to a workflow |
| `temperaLlm` | tempera-llm | `contracts/openapi/llm.openapi.json` | no | drift only (`regen-contract.sh --check`) |
| `temperaDocument` | tempera-document | `contracts/openapi/document.openapi.json` | no | drift only (`check-contract-sync.sh`) |
| `temperaVoice` | tempera-voice | `contracts/openapi/voice.openapi.json` | no — being wired now | `export-openapi.py --check` |
| `temperaClearing` | tempera-clearing | `contracts/openapi/clearing.openapi.json` | no | `contract-spine.yml` + a Rust test |
| `cradle` | cradle | `contracts/openapi/cradle.openapi.json` | no | migrating |
| `remi` | remi | `contracts/openapi/remi.openapi.json` | no | migrating |
| `temperaWorkflows` | tempera-workflows | `contracts/openapi/workflows.openapi.json` | no | migrating |

All of the above are OpenAPI **3.1.0**. All declare
`x-tempera-protocol-routes` except `tempera-business`, which has no protocol
routes to declare.

**`tempera-connectors` is the worked example.** It is a producer with a real
gate: canonical path, the three files vendored under `.tempera/agent-kit/`, and
a dedicated `Producer contract standard` job in `.github/workflows/ci.yml`
running

```sh
python3 .tempera/agent-kit/scripts/lint_producer_contract.py \
  --product temperaConnectors \
  --audience tempera-connectors \
  contracts/openapi/connectors.openapi.json
```

Copy that job. It is deliberately a separate job so a contract failure is
legible as a contract failure rather than buried in a test matrix.

**`tempera-business` and `tempera-dropshipping` are new producers**, added
since the previous version of this file. Both are `oauthResource`-bound
(`AUDIENCE_BOUND_PRODUCTS` in `sync-openapi-surface.py`), both vendor the
linter, and both run it in CI.

## Producers still on a legacy path

Registered in `PRODUCTS` at a non-canonical location. Moving one means moving
the file **and** its registry entry in the same change, or vendoring breaks.

| Product key | Repository | Contract path | Format |
| --- | --- | --- | --- |
| `controlPlane` | auth-hub | `contracts/control-plane.openapi.json` | OpenAPI 3.1.0 JSON |
| `dataEngine` | data-engine | `api/openapi.yaml` | OpenAPI **YAML** |
| `humanData` | human-data | `api/openapi.json` | OpenAPI 3.1.0 JSON |
| `palette` | palette | `sdks/openapi/palette-api.json` | OpenAPI 3.1.0 JSON |
| `tempo` | tempo | `api/openapi.json` | OpenAPI 3.1.0 JSON |
| `temperaBio` | tempera-bio | `openapi/tempera-bio-discovery-v1.openapi.json` | OpenAPI 3.1.0 JSON |

Two are not merely mislocated but the wrong artefact, and both are known debt:

- **`data-engine`** publishes YAML, vendored through a `yaml-json-local-bundle`
  transform. New producers publish JSON; do not add a third format.
- **`remi`**'s registered `docs/public-http-contract.json` is not an OpenAPI
  document at all — it is a bespoke `"contract_kind": "http-route-manifest"`.
  Its canonical `contracts/openapi/remi.openapi.json` is what replaces it.

## Registry drift to be aware of

At the time of writing, the registry lags the repositories in several places —
a `PRODUCTS` entry still pointing at a path a producer has already vacated, and
`temperaDropshipping` / `temperaBusiness` pinned to feature branches rather
than `main`. This is exactly what the propagation loop is for: re-vendoring
resolves it, and a registry path that no longer exists fails loudly at
`sync-vendored-openapi.py` rather than silently.

If you are moving a producer to the canonical path, the complete change is:

1. Move the file to `contracts/openapi/<product>.openapi.json` and make the
   generator emit it there.
2. Vendor the kit (`python3 scripts/sync-agent-kit.py`, or ask for a fanout)
   so `.tempera/agent-kit/` exists, and add the lint job to CI.
3. Run the linter and fix what it finds — do not baseline it.
4. Update `source_path` (and `source_branch`, if it was a feature branch) in
   `PRODUCTS`.
5. Re-vendor: `python3 scripts/revendor-product.py --products <key>` in
   `tempera-sdk`.

## Repositories with no HTTP surface

`tempera-chain`, `tempera-cyber`, `tempera-graph`, `tempera-math`,
`tempera-physics`, `tempera-satellite`, `tempera-autopsy`, `tempera-evals`,
`tempera-code`, `tempera-mcp`, `agent-browser`, `business-logic`,
`logistics-data`, `github-evals`, `investor-outreach`, `public-site`,
`tempera-android`, `tempera-gtm`, `tempOS`, `temp.js`.

These carry this skill so that a service added later starts in the right shape,
not to imply they publish a contract today. The kit's `notify-sdk.yml` is inert
in them: it only triggers on a push touching `contracts/openapi/**`.

`tempera-main` (coordination) and `tempera-demo` (customer-facing sample) are
excluded from distribution entirely.

## The `.source` pin

Vendoring writes `specs/<name>.json` plus `specs/<name>.json.source`:

```json
{
  "source_repo": "tempera-dev/tempera-clearing",
  "source_branch": "main",
  "source_commit": "<40 hex>",
  "source_path": "contracts/openapi/clearing.openapi.json",
  "source_blob_sha": "<git blob>",
  "source_sha256": "<sha256 of the source bytes>",
  "generated_path": "specs/tempera-clearing-api.json",
  "generated_sha256": "<sha256 of the vendored bytes>",
  "generated_with": "source_lock.py@2+inline-local-json-ref-bundle",
  "source_dependencies": [ "… inlined local schema files …" ]
}
```

Anyone can reproduce the vendored file with `git show <commit>:<path>` plus the
named transform. If they cannot, the pin is invalid regardless of what CI said.
Vendoring at a branch name, a tag, or a short SHA is refused.

**Exact-source verification now covers every vendored producer.** The matrix in
`tempera-sdk/.github/workflows/test.yml` is generated from `PRODUCTS` by
`scripts/gen-exact-source-matrix.py`, so a product is in the registry or it is
not vendored at all — it cannot be forgotten into an unverified state with a
green build, which is what used to happen.

Consequently `tempera-sdk/contracts/sdk-exact-source-gaps.json` is **empty by
design**, and `check-exact-source-gaps.py` refuses a gap for any repository the
matrix already covers. Such a gap is not a blocker; it is stale paperwork
hiding the fact that verification is already running, which is how `tempera-bio`,
`human-data`, `remi`, and `tempo` stayed out of CI for months behind an
expiring note.
