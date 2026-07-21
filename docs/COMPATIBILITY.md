# SDK compatibility ledger

## 2026-07-21 — remove phantom Control Plane model-profile methods

- **Class:** corrective breaking consumer change.
- **Owner:** Contract Spine.
- **Removed:** `listModelProfiles`, `getModelProfile`, `createModelProfile`,
  `updateModelProfile`, and `deleteModelProfile` in TypeScript, Python, and
  Rust.
- **Producer evidence:** `tempera-dev/auth-hub` commit
  `d59222ff6f54374d82cee4f5b04a2080112ef945`,
  `contracts/control-plane.openapi.json`, blob
  `5723eb65d8fc9fef3041216fab138763563ae7f5`, SHA-256
  `957b0ab9e0fd7b5a0a5ad88fcb0563c67918162e741c1806187d9b291ae21c02`.
  The exact 61-operation producer contract has no `/model-profiles` route.
- **Consumer evidence:** organization code search found no release-path usage
  outside the SDK's own generated surface and documentation. Calls could only
  receive the producer's `404 not_found`; there is no functioning behavior to
  preserve.
- **Migration:** remove calls to these methods. There is no replacement
  operation. Use a future generated method only after Auth Hub publishes a
  reviewed canonical route.
- **Rollout:** release as aggregate SDK `0.7.0`; exact-source and all-language
  checks must pass before merge.
- **Rollback:** do not restore phantom methods. If a legitimate producer route
  lands, add it source-first as a new compatible SDK operation.
- **Affected consumers:** aggregate TypeScript, Python, and Rust SDK users.
