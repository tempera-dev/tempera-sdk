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

## Current Status

This is the first aggregated scaffold. It intentionally exposes common product names, endpoint routing, scope validation, bearer auth headers, and typed request options before deeper generated clients land from each product contract.

## Verification

```sh
python3 scripts/check-sdk-surface.py
npm --prefix packages/typescript test
python3 -m unittest discover -s packages/python/tests
cargo test --manifest-path packages/rust/Cargo.toml
```
