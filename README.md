# Tempera SDK

One versioned SDK contract in TypeScript, Python, and Rust. The primary product
story is a browser-agent quality loop: the control plane provisions access,
Tempo runs and records a browser session, Human Data reviews the provisioned
session and trace evidence, and Palette holds and measures the corresponding
trace. The onboarding-provisioned integration supplies the correlation path; a
Tempo session does not by itself prove a Palette trace exists. A single manifest,
[`surface.json`](./surface.json), keeps that workflow and the full private
contract inventory aligned across languages.

## Access status

Hosted Tempera services are in private design-partner access. Onboarding
provides the SDK package access, issuer URL, credentials, environment, and any
product-specific base URLs for your workspace. Start with the provisioned
staging environment unless Tempera explicitly approves another target.

The `production` preset and `api.tempera.dev` entries remain part of the SDK's
versioned target contract; their presence does not mean production access is
generally available or that the control plane is production-ready.

## Primary browser-agent workflow

| Client | Product | Typed operations | Audience |
|---|---|---|---|
| `controlPlane` / `control_plane` | [auth-hub](https://github.com/tempera-dev/auth-hub) — accounts, OAuth, workspaces, API keys, billing, usage | 44 | account tokens |
| `tempo` | [tempo](https://github.com/tempera-dev/tempo) — agent-native browser (tempod) | 18 | `tempo` |
| `humanData` / `human_data` | [human-data](https://github.com/tempera-dev/human-data) — reviewers inspect provisioned browser-session evidence, record decisions, and return candidate cases to the quality loop | passthrough; no typed operations yet | `human-data` |
| `palette` | [palette](https://github.com/tempera-dev/palette) — agent observability, traces, datasets, evals | 15 | `palette` |

Human Data is a provisioned review workflow, not a published raw HTTP route.
Use only the endpoint contract supplied during onboarding.

## Versioned private contract inventory

The SDK retains the following clients for compatibility and complete reference
coverage. Their presence in the registry does not advertise public availability,
a live hosted service, or an undocumented endpoint.

| Client | Product | Typed operations | Audience |
|---|---|---|---|
| `cradle` | [cradle](https://github.com/tempera-dev/cradle) — capability sandbox | 10 | `cradle` |
| `temperaLlm` / `tempera_llm` | [tempera-llm](https://github.com/tempera-dev/tempera-llm) — OpenAI-compatible LLM gateway (chat completions, responses, models) | 4 | `tempera-llm` |
| `temperaWorkflows` / `tempera_workflows` | [tempera-workflows](https://github.com/tempera-dev/tempera-workflows) — deterministic bounded-DAG workflow engine (definitions, validation, runs; run SSE events via passthrough) | 12 | `tempera-workflows` |
| `temperaGym` / `tempera_gym` | [tempera-gym](https://github.com/tempera-dev/tempera-gym) — RL environment pack (catalog, synchronous rollouts, trajectory-v1 runs) | 5 | `tempera-gym` |
| `remi` | [remi](https://github.com/tempera-dev/remi) — temporal memory | 12 | `remi` |
| `dataEngine` / `data_engine` | [data-engine](https://github.com/tempera-dev/data-engine) — label-emergence engine: ingestion, verification, RL/eval/SFT emission | 87 | `data-engine` |
| `tempJs`, `tempOS`, `arrha` | [temp.js](https://github.com/tempera-dev/temp.js), [tempOS](https://github.com/tempera-dev/tempOS), [Arrha](https://github.com/tempera-dev/arrha) | passthrough; no typed operations yet | — |

Palette also ships seven fully generated per-language clients inside its own
repo (`sdks/clients/`) covering all 55+ operations of its OpenAPI contract;
this SDK's palette client covers the core read/ingest/dataset/admin loop and
defers exhaustive coverage to those.

## Unified auth

Your provisioned control-plane URL is an OAuth 2.1 issuer:
authorization-code + PKCE (S256, public clients), refresh-token rotation, and
RFC 8707 `resource` audience selection (`palette` default; `tempo`, `cradle`,
`remi`, `human-data`, `data-engine`, `tempera-mcp` registered). One account mints one token
per product audience, and control-plane API keys (`tp_...`) work as bearers
at every product via central introspection.

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

- `surface.json` is the single source of truth for SDK ergonomics;
  data-engine owns the canonical REST operation identities in OpenAPI.
  `scripts/gen-sdk-surface.py` renders the per-language surface tables and
  `scripts/gen-sdk-docs.py` the Mintlify docs site (both committed, both
  drift-gated).
- `scripts/check-sdk-surface.py` gates: manifest invariants, regenerate-and-
  diff (surface tables and docs site), one version across the three packages,
  uniform-primitive markers, and data-engine operation/path/method parity.
- `contracts/data-engine-openapi-operations.json` is a checked operation lock
  generated from data-engine's authoritative committed OpenAPI. Its provenance
  includes the repository, branch, 40-character commit, path, Git blob,
  content SHA-256, generator version, and generated-operation digest. The sync
  rejects dirty producer checkouts and reads source bytes with `git show`.
  When both repositories are checked out, refresh and verify it with
  `python3 scripts/sync-data-engine-openapi.py --check`; CI always verifies
  bidirectional parity: no phantom SDK method and no omitted producer route.
- Each package's test suite loops over **every** generated operation against
  a mock transport, asserting method, path, auth header, and body defaults.
- The endpoint-change rollout process is documented in
  [`docs/ROLLOUT.md`](./docs/ROLLOUT.md).

## Verification

```sh
npm test   # surface gate + TypeScript + Python + Rust suites
```

or individually:

```sh
python3 scripts/check-sdk-surface.py
python3 scripts/sync-data-engine-openapi.py --check
npm --prefix packages/typescript test
PYTHONPATH=packages/python/src python3 -m unittest discover -s packages/python/tests
cargo test --manifest-path packages/rust/Cargo.toml
```
