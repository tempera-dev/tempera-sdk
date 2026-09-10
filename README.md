# Tempera SDK

One versioned SDK contract in **TypeScript, Python, Rust, Swift, Kotlin, C, and
C++** — generated, not hand-written, so an application in any of them calls a
Tempera product directly rather than through a wrapper.

A single manifest, [`surface.json`](./surface.json), is the source every
language is rendered from. It is itself derived: each producer publishes an
OpenAPI contract at `contracts/openapi/<product>.openapi.json`, the SDK vendors
that contract at an exact commit with a verifiable source lock, and the surface
is regenerated from what was vendored. Nobody copies a spec between
repositories by hand, and a producer that moves its contract breaks the build
loudly rather than silently serving a stale one.

The primary product story is a browser-agent quality loop: the control plane
provisions access, Tempo runs and records a browser session, Human Data reviews
the provisioned session and trace evidence, and Palette holds and measures the
corresponding trace. The onboarding-provisioned integration supplies the
correlation path; a Tempo session does not by itself prove a Palette trace
exists.

## Access status

Hosted Tempera services are in private design-partner access. Onboarding
provides the SDK package access, issuer URL, credentials, environment, and any
product-specific base URLs for your workspace. Start with the provisioned
staging environment unless Tempera explicitly approves another target.

The `production` preset and `api.tempera.dev` entries remain part of the SDK's
versioned target contract; their presence does not mean production access is
generally available or that the control plane is production-ready.

## Clients

Every client below is generated from the vendored producer contract, so the
operation counts are what the SDK actually exposes rather than what someone
remembered to write down. Presence in the registry does not advertise public
availability, a live hosted service, or an undocumented endpoint.

<!-- BEGIN generated client table -->

| Client | Product | Typed operations | Audience |
| --- | --- | --- | --- |
| `controlPlane` | [auth-hub](https://github.com/tempera-dev/auth-hub) | 123 | — |
| `dataEngine` | [data-engine](https://github.com/tempera-dev/data-engine) | 66 | `data-engine` |
| `palette` | [palette](https://github.com/tempera-dev/palette) | 61 | `palette` |
| `temperaPayments` | [tempera-payments](https://github.com/tempera-dev/tempera-payments) | 47 | `tempera-payments` |
| `temperaRisk` | [tempera-risk](https://github.com/tempera-dev/tempera-risk) | 44 | `tempera-risk` |
| `temperaDropshipping` | [tempera-dropshipping](https://github.com/tempera-dev/tempera-dropshipping) | 31 | `tempera-dropshipping` |
| `tempo` | [tempo](https://github.com/tempera-dev/tempo) | 27 | `tempo` |
| `temperaInvestigations` | [tempera-investigations](https://github.com/tempera-dev/tempera-investigations) | 24 | `tempera-investigations` |
| `temperaVoice` | [tempera-voice](https://github.com/tempera-dev/tempera-voice) | 24 | `tempera-voice` |
| `temperaGym` | [tempera-gym](https://github.com/tempera-dev/tempera-gym) | 22 | `tempera-gym` |
| `temperaWorkflows` | [tempera-workflows](https://github.com/tempera-dev/tempera-workflows) | 21 | `tempera-workflows` |
| `cradle` | [cradle](https://github.com/tempera-dev/cradle) | 18 | `cradle` |
| `temperaBusiness` | [tempera-business](https://github.com/tempera-dev/tempera-business) | 15 | `tempera-business` |
| `temperaDocument` | [tempera-document](https://github.com/tempera-dev/tempera-document) | 15 | `tempera-document` |
| `temperaBio` | [tempera-bio](https://github.com/tempera-dev/tempera-bio) | 14 | `tempera-bio` |
| `remi` | [remi](https://github.com/tempera-dev/remi) | 11 | `remi` |
| `temperaClearing` | [tempera-clearing](https://github.com/tempera-dev/tempera-clearing) | 8 | `tempera-clearing` |
| `temperaConnectors` | [tempera-connectors](https://github.com/tempera-dev/tempera-connectors-runtime) | 8 | `tempera-connectors` |
| `temperaLlm` | [tempera-llm](https://github.com/tempera-dev/tempera-llm) | 5 | `tempera-llm` |
| `humanData` | [human-data](https://github.com/tempera-dev/human-data) | 3 | `data-engine` |
| `arrha` | [Arrha](https://github.com/tempera-dev/arrha) | passthrough; no typed operations | — |
| `tempJs` | [temp.js](https://github.com/tempera-dev/temp.js) | passthrough; no typed operations | — |
| `tempOS` | [tempOS](https://github.com/tempera-dev/tempOS) | passthrough; no typed operations | — |

<!-- END generated client table -->

Four entries deserve a note.

**`controlPlane`** is the Auth Hub. Its account-plane routes are fenced by
workspace role rather than by OAuth scope — `account:session`,
`account:orgAdmin`, `account:billingAdmin`, `account:credentialAdmin`,
`account:platformStaff` — and those roles are deliberately *not* grantable,
because a long-lived `tp_` key must never be able to administer an
organization. `surface.json` records them under `accountPermissions`, separate
from `scopes`, and the surface gate refuses any string that appears in both.

**`humanData`** is a provisioned review workflow whose typed operations are
generated from the exact producer OpenAPI; their presence does not advertise
unrestricted hosted access. It authenticates against the `data-engine`
audience rather than one of its own.

**`palette`** covers every ordinary JSON operation in the current producer
OpenAPI. Its raw OTLP collector route is an explicit transport exclusion and
should be called through an OTLP exporter, not the aggregate JSON dispatcher.

**`tempJs`, `tempOS` and `arrha`** are passthrough clients with no typed
operations yet.

Tempera Code is intentionally not an aggregate HTTP product client. Its public
contract is the app-server JSON-RPC protocol and its generated protocol SDKs.

## Unified auth

Your provisioned control-plane URL is an OAuth 2.1 issuer:
authorization-code + PKCE (S256, public clients), refresh-token rotation, and
RFC 8707 `resource` audience selection. One account mints one token per product
audience, and control-plane API keys (`tp_...`) work as bearers at every
product via central introspection.

The registered audiences and scopes are not listed here, because a list in
prose goes stale: read `audiences`, `scopes` and `accountPermissions` in
[`surface.json`](./surface.json), which is generated from the Auth Hub's own
contract. A scope a producer declares but the Auth Hub has not registered
appears in `scopeGaps` with an owner and a migration, so the omission is
visible rather than silent.

Note that a workflow spanning several products needs several tokens — each
operation carries its own `authKind`, `authAudience` and `scope` in the
surface, and one audience's token is not accepted by another.

```js
import { TemperaAuth, createPkcePair, createTemperaClient } from "@tempera/sdk";

const issuerUrl = process.env.TEMPERA_ISSUER_URL;
const clientId = process.env.TEMPERA_CLIENT_ID;
if (!issuerUrl || !clientId) throw new Error("Missing provisioned Tempera auth settings");

const auth = new TemperaAuth({ issuerUrl, clientId });

// Browser/device flow: send the user to the authorize URL, then exchange the code.
const { verifier, challenge } = await createPkcePair();
const authorizeUrl = auth.buildAuthorizeUrl({
  redirectUri: "https://my-app.example/callback",
  codeChallenge: challenge,
  audience: "tempo",
  scope: ["trace:read", "trace:write"],
});
await auth.exchangeCode({ code, codeVerifier: verifier, redirectUri, audience: "tempo" });
await auth.refresh("tempo"); // rotation: stores the newly issued refresh token

// Or headless: one tp_ API key covers every audience.
const apiKey = process.env.TEMPERA_API_KEY;
if (!apiKey) throw new Error("Missing provisioned TEMPERA_API_KEY");
const headless = new TemperaAuth({ issuerUrl, apiKey });
```

## Browser-agent quickstart

```js
import { TemperaAuth, createTemperaClient } from "@tempera/sdk";

const issuerUrl = process.env.TEMPERA_ISSUER_URL;
const apiKey = process.env.TEMPERA_API_KEY;
const tenantId = process.env.TEMPERA_TENANT_ID;
if (!issuerUrl || !apiKey || !tenantId) {
  throw new Error("Missing provisioned Tempera settings");
}
const client = createTemperaClient({
  auth: new TemperaAuth({ issuerUrl, apiKey }),
  environment: "staging",
});

// Control plane: confirm the provisioned issuer contract.
const issuerMetadata = await client.controlPlane.discovery();

// Tempo runs and records the browser session.
const session = await client.tempo.createSession({ url: "https://example.com" });

// Session creation does not prove a Palette trace exists. Onboarding supplies
// the integration and correlation path for the corresponding Palette evidence.
// Human Data reviews the provisioned session and trace evidence.

// Palette holds and measures traces available for this tenant.
const availableTraces = await client.palette.listTraces({ tenant_id: tenantId, limit: 20 });
```

Python is the same surface in snake_case (`client.control_plane.discovery()`,
`client.palette.list_traces(...)`); Rust builds `RequestSpec`s for your HTTP
client (`client.build_request("palette", "list_traces", &params)`) since the
crate ships no HTTP stack. Parameters use wire names (snake_case) in every
language.

## Code-validation evidence

The Data Engine client is the full-stack API for repository-validation data.
GitHub capture workers retain source artifacts, then publish typed policies,
assessments, and evaluation trials through the existing immutable evidence and
episode resources. The SDK operation lock is generated from Data Engine commit
`6c889513d550e2c8fab1c35ac9f8cd667f90703e`; this is contract provenance, not a
claim that a hosted GitHub App or validation service is generally available.

```js
const policy = await client.dataEngine.createEvidenceRecord({
  parent: `projects/${projectId}`,
  schemaVersion: "data-engine.evidence-record.v1",
  domain: "tempera.code-validation",
  evidenceType: "validation-policy",
  payloadSchema: "gray.validation-policy.v1",
  payload: approvedPolicy,
  sourceArtifactRefs: [policySourceArtifactName],
  verificationState: "UNVERIFIED",
});

const assessment = await client.dataEngine.createEvidenceRecord({
  parent: `projects/${projectId}`,
  schemaVersion: "data-engine.evidence-record.v1",
  domain: "tempera.code-validation",
  evidenceType: "validation-assessment",
  payloadSchema: "gray.validation-assessment.v1",
  payload: exactRevisionAssessment,
  sourceArtifactRefs: [repositoryCaptureArtifactName],
  verificationState: "UNVERIFIED",
});

const trial = await client.dataEngine.createEpisode({
  parent: `projects/${projectId}`,
  schemaVersion: "data-engine.episode.v1",
  domain: "tempera.code-validation",
  contextEvidenceRef: assessment.name,
  environmentRef: exactRepositorySnapshot,
  seed: 7,
  observations: [{ policyRef: policy.name }],
  measuredOutcomes: { decision: "NEEDS_EVIDENCE" },
  verifierResults: [{ verifierRef: "gray.validation-assessment", status: "ABSTAIN" }],
  rewardComponents: { validationDecision: 0 },
  terminalReason: "validation-needs-evidence",
});
```

Python uses `client.data_engine.create_evidence_record(...)` and
`client.data_engine.create_episode(...)` with the same lowerCamel wire keys. A
`PASS` record must carry the retained verifier receipt required by Data Engine;
review text or a model assertion alone is not sufficient.

## Signed evaluation evidence

The Palette client includes three generated, `eval:run`-scoped operations from
the real Palette Rust handlers: `importTemperaBundle`,
`recordTemperaDecision`, and `getTemperaEvidence` (snake_case in Python and
Rust). Their generated OpenAPI is pinned to Palette revision
`8ee730e5d7c82ae7aa8f828a36087c24424c217b`, artifact digest
`sha256:26780d59182f0fc362df438b0227f54f5594a620f9ace5313f48587a8e901dc0`,
and the merged evidence contract from
[Palette PR #16](https://github.com/tempera-dev/palette/pull/16).

`tempera-evals palette-evidence-handoff` produces the canonical JSON,
signature, and public key body after independently verifying the suite evidence
and the exact Palette contract. The artifact contains no credential. The SDK
adds the caller's provisioned Palette bearer only when sending it:

```js
import { readFile } from "node:fs/promises";
import { TemperaAuth, createTemperaClient } from "@tempera/sdk";

const issuerUrl = process.env.TEMPERA_ISSUER_URL;
const apiKey = process.env.TEMPERA_API_KEY;
const tenantId = process.env.TEMPERA_TENANT_ID;
const projectId = process.env.TEMPERA_PROJECT_ID;
const handoffPath = process.env.TEMPERA_EVAL_HANDOFF_PATH;
if (!issuerUrl || !apiKey || !tenantId || !projectId || !handoffPath) {
  throw new Error("Missing provisioned Palette or eval-handoff settings");
}

const handoff = JSON.parse(await readFile(handoffPath, "utf8"));
const client = createTemperaClient({
  auth: new TemperaAuth({ issuerUrl, apiKey }),
  environment: "staging",
});
const receipt = await client.palette.importTemperaBundle({
  tenant_id: tenantId,
  project_id: projectId,
  canonical_json: handoff.request.body.canonical_json,
  signature_base64: handoff.request.body.signature_base64,
  public_key_pem: handoff.request.body.public_key_pem,
});
```

Palette independently verifies canonicalization, self-digest, signature,
trusted release key, official readiness, leakage policy, scope, idempotency,
and conflicts. The receipt is minimal and never returns the raw signed payload.

## Errors

Every product speaks a different wire error shape; the SDK normalizes all of
them into one `TemperaApiError` with `status`, `code`, `message`,
`requestId`, `product`, `operation`, and the raw `body` — identical fields in
all three languages. MCP JSON-RPC errors raise `TemperaMcpError` with the
gateway's numeric `code` (`-32002` means `plan_limit_exceeded`).

## MCP gateway

The unified MCP gateway lives at `${issuer}/mcp` (audience `tempera-mcp`,
scope `mcp:invoke`) and aggregates every product MCP server behind namespaced
tools (`palette_*`, `tempo_*`, `cradle_*`, `remi_*`, `data_engine_*`).

```js
import { TemperaMcpClient } from "@tempera/sdk";
const mcp = new TemperaMcpClient({ auth });   // url derives as ${issuer}/mcp
await mcp.initialize();
const tools = await mcp.listTools();
await mcp.callTool("cradle_get_capabilities");
console.log(await mcp.whoami());
```

## Documentation

The documentation site lives in [`docs/site/`](./docs/site) — a complete
[Mintlify](https://mintlify.com) project (`docs.json` + MDX pages) generated
from `surface.json` (and `docs/ROLLOUT.md`) by
[`scripts/gen-sdk-docs.py`](./scripts/gen-sdk-docs.py): overview, auth,
environments, errors, MCP gateway, rollout, and one API-reference page per
typed product covering every operation with tabbed TS/Python/Rust examples.

The docs are auto-updated by construction: `scripts/check-sdk-surface.py`
re-renders the site and fails on any diff, so CI rejects a `surface.json`
change that doesn't regenerate the docs. After editing the manifest run:

```sh
python3 scripts/gen-sdk-surface.py && python3 scripts/gen-sdk-docs.py
```

To deploy, point the Mintlify GitHub app at this repo with `docs/site` as the
content directory — it auto-deploys on every push to `main` (no build step;
the committed site is always current thanks to the drift gate).

## Uniformity, tests, and rollout

- [`scripts/product_registry.py`](./scripts/product_registry.py) is the one
  table of producers. Registering a producer used to mean editing five
  hand-maintained dictionaries with no way of noticing when they disagreed, so
  a producer added to four of the five vendored and generated but silently
  skipped a gate. The vendoring table, the spec-name maps and the default-auth
  map are all derived from it now, and a partial registration is not
  expressible.
- [`docs/CONTRACT_STANDARD.md`](./docs/CONTRACT_STANDARD.md) is the normative
  standard a producer's contract has to meet, and
  [`scripts/lint_producer_contract.py`](./scripts/lint_producer_contract.py)
  runs it. The same file is distributed to every producer through the auth-hub
  agent kit and byte-verified against this copy, so a contract that passes in
  the producer's own CI cannot fail once the SDK vendors it.
- `python3 scripts/revendor-product.py --products all` is the whole
  producer-to-SDK chain in one command: contract at an exact producer commit →
  `specs/<product>.openapi.json` plus its `.source` lock → `surface.json` →
  the generated surface table in every language → the docs site. Running the
  steps by hand in the wrong order used to be possible and left a
  `surface.json` no committed spec produced.
- `.github/workflows/contract-updated.yml` runs that chain on a schedule, on a
  `repository_dispatch` from a producer, and on demand, then opens a pull
  request with the result.
- `surface.json` is the single source of truth for SDK ergonomics;
  data-engine owns the canonical REST operation identities in OpenAPI.
  `scripts/gen-sdk-surface.py` renders the per-language surface tables,
  `scripts/gen-sdk-docs.py` the Mintlify docs site, and
  `scripts/gen-producer-tables.py` the producer and client tables in this
  README and in the rollout docs (all committed, all drift-gated).
- `scripts/check-sdk-surface.py` gates: manifest invariants, regenerate-and-
  diff (surface tables and docs site), one version across all seven packages,
  uniform-primitive markers, data-engine operation/path/method parity, and the
  exact source-pinned Palette evidence contract.
- `scripts/check-aip-conformance.py` is the Google Cloud AIP migration
  ratchet. It rejects new or stale mechanical violations across every vendored
  producer contract while keeping protocol-native MCP, OAuth, OTLP, webhook,
  WebSocket/BiDi, and SSE routes explicit. The breaking producer-first
  migration order is documented in
  [`docs/AIP_CONFORMANCE.md`](./docs/AIP_CONFORMANCE.md).
- `contracts/palette-eval-openapi-operations.json` binds the three SDK methods
  to Palette's generated operation IDs, request/receipt schemas, failure
  responses, and immutable source receipt. Refresh it only from a clean,
  exact Palette commit with `python3 scripts/sync-palette-eval-openapi.py`.
- `contracts/data-engine-openapi-operations.json` is a checked operation and
  auth lock generated from data-engine's authoritative committed OpenAPI. Its
  provenance
  includes the repository, branch, 40-character commit, path, Git blob,
  content SHA-256, generator version, and generated-operation digest. The sync
  rejects dirty producer checkouts and reads source bytes with `git show`.
  When both repositories are checked out, refresh and verify it with explicit
  `--source-repo`, `--source-branch`, and 40-character `--source-commit`
  arguments; detached exact-commit producer checkouts are supported. SDK CI
  verifies the committed lock and generated surface in both directions,
  including exact per-operation audience and scope parity.
- `specs/data-engine-mcp-admission.json` and
  `specs/data-engine-mcp-tools.json` vendor the producer's exact curated MCP
  decisions and static `tools/list` serialization. Their adjacent `.source`
  locks bind the same immutable Data Engine commit as the OpenAPI lock. The SDK
  gate requires every authenticated project operation to be explicitly
  exposed or denied, verifies the producer-declared exposed/denied counts, and
  rejects scope, schema-fixture, or catalog drift without turning REST coverage
  into model exposure.
- Each package's test suite loops over **every** generated operation against
  a mock transport, asserting method, path, auth header, and body defaults.
- `contracts/sdk-exact-source-gaps.json` records any temporary, expiring
  hosted-verification blocker. It is currently empty: every private producer
  in the upstream matrix uses the organization-wide, least-privilege Contract
  Reader App and reproduces the exact vendored SHA from committed source. A
  future exception must name its exact commit, owner, remediation, producer CI,
  and review date; it must never silently bypass the source gate.
- `contracts/native-transport-v1.json` is the native transport contract for
  the hand-written Kotlin and Swift clients in tempera-mobile and tempera-iOS,
  which do not consume the generated packages. For every operation a phone may
  call it publishes the method, path template, auth audience, scope, retry
  class, and request/response digests derived from the vendored producer
  contract: every tempera-dropshipping and tempera-business operation, the
  phone-relevant tempera-voice session, pending-action, and agent operations,
  and one synthetic `WSS` operation, `temperaVoice.streamVoiceSession`, taken
  from the voice contract's `x-tempera-websocket-contract`. Each producer
  entry records the exact mainline commit its vendored contract is locked to.
  `scripts/check-native-transport.py` regenerates the file (`--write`), fails
  when it is stale, and with `--client PATH` checks a native source file:
  every `// tempera-transport: <product>.<op> <METHOD> <path>` annotation must
  name a published operation with the exact method and path template and sit
  directly above a call whose string literal has the same route shape (a
  `WSS` annotation is checked the same way), and every literal that reaches
  into a producer's canonical namespace (`/v1/organizations` for dropshipping;
  `/v1/operating-state`, `/v1/business-profile`, `/v1/cases` for business;
  `/v1/sessions`, `/v1/agents`, `/v1/actions` for voice) must be annotated.
- The endpoint-change rollout process is documented in
  [`docs/ROLLOUT.md`](./docs/ROLLOUT.md).

## Verification

```sh
npm test   # surface gate + the language suites
```

The gates, individually:

```sh
python3 scripts/check-sdk-surface.py        # manifest invariants, regenerate-and-diff, one version across seven packages
python3 scripts/check-aip-conformance.py    # the AIP ratchet over every vendored producer contract
python3 scripts/check-upstream-drift.py     # bidirectional: no phantom SDK routes, no unaccounted producer routes
python3 scripts/check-exact-source-gaps.py  # every vendored producer is verified commit-by-commit in CI
python3 scripts/check-native-transport.py   # hand-written phone clients stay inside the published contract
python3 scripts/sync-openapi-surface.py --check
python3 scripts/gen-producer-tables.py --check
```

One producer's contract, linted the way its own CI lints it:

```sh
python3 scripts/lint_producer_contract.py \
  ../tempera-voice/contracts/openapi/voice.openapi.json \
  --product temperaVoice --audience tempera-voice
```

The language suites:

```sh
npm --prefix packages/typescript test
PYTHONPATH=packages/python/src python3 -m unittest discover -s packages/python/tests
cargo test --manifest-path packages/rust/Cargo.toml
swift test --package-path packages/swift
./gradlew -p packages/kotlin test
cc -std=c99 -Wall -Wextra -Werror -pedantic -Ipackages/c/include \
  packages/c/tests/test_tempera.c packages/c/src/*.c -o /tmp/tempera-c-tests && /tmp/tempera-c-tests
c++ -std=c++20 -Wall -Wextra -Werror -pedantic -Ipackages/cpp/include \
  packages/cpp/tests/test_tempera.cpp -o /tmp/tempera-cpp-tests && /tmp/tempera-cpp-tests
```

For an unpublished exact-source train, synchronizers accept
`--allow-local-source` only when the requested SHA equals a clean checkout's
named local branch and `HEAD`. Use `python3 scripts/check-sdk-surface.py
--staged-local` for that local qualification. The default command above remains
strict and rejects non-`main` source locks for release.
