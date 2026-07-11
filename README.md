# Tempera SDK

Aggregated SDKs for Tempera products across TypeScript, Python, and Rust.

This repository is the public SDK surface for:

- `auth-hub`: hosted auth, OAuth, API keys, org/project/environment context, billing handoff, and shared account contracts.
- `tempo`: agent-native browser and headless observation runtime.
- `temp.js`: durable JavaScript runtime bridge for Tempera agents.
- `tempOS`: OS/runtime admission, policy, and receipt layer for agents.
- `remi`: temporal memory and retrieval for agent systems.
- `cradle`: capability sandbox execution layer for agents.
- `Arrha`: settlement, chain, credits, and indexer layer for agent payments.

The product implementation repos stay separate. This repo gives application teams one place to install clients, share auth handling, and call the products with the same workspace and permission model.

## Packages

```sh
packages/typescript
packages/python
packages/rust
```

## Unified Tempera auth

The control plane (`auth-hub`, e.g. `https://api.tempera.dev`) is an OAuth2
authorization server: authorization-code + PKCE (S256 required, public
clients), refresh-token rotation, and RFC 8707 `resource` audience selection
(`palette` is the default; `tempo`, `cradle`, `remi`, `human-data`, and
`tempera-mcp` are also registered). One unified account mints one token per
product audience, and control-plane API keys (`tp_...`) work as bearers at
every product via central introspection. The unified MCP gateway lives at
`${issuer}/mcp` (audience `tempera-mcp`, scope `mcp:invoke`).

All three packages expose the same surface: PKCE helpers, an authorize-URL
builder that carries `resource=<audience>`, code exchange / refresh / revoke
against `/oauth/token` and `/oauth/revoke` (refresh rotation is handled — the
newly issued refresh token replaces the old one), and product clients that
attach the audience-matched bearer.

```js
import { TemperaAuth, createPkcePair, createTemperaProducts } from "@tempera/sdk";

const auth = new TemperaAuth({ issuerUrl: "https://api.tempera.dev", clientId: "my-app" });

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

// Or headless: one API key covers every audience.
const headless = new TemperaAuth({ issuerUrl: "https://api.tempera.dev", apiKey: process.env.TEMPERA_API_KEY });

const products = createTemperaProducts({ auth, baseUrls: { tempo: "https://tempo.tempera.dev" } });
await products.tempo("/v1/traces");   // Authorization: Bearer <tempo token>
console.log(products.mcpUrl);         // https://api.tempera.dev/mcp
```

Python mirrors this with `tempera_sdk.TemperaAuth` / `TemperaProducts`, and the
Rust crate exposes `tempera_sdk::auth::TemperaAuth` (URL and form-body builders
plus `apply_token_response` for rotation, since the crate ships no HTTP client).

## Current Status

This is the first aggregated scaffold. It intentionally exposes common product names, endpoint routing, scope validation, bearer auth headers, and typed request options before deeper generated clients land from each product contract.

## Verification

```sh
python3 scripts/check-sdk-surface.py
npm --prefix packages/typescript test
python3 -m unittest discover -s packages/python/tests
cargo test --manifest-path packages/rust/Cargo.toml
```
