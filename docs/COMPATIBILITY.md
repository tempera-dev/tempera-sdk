# SDK compatibility ledger

## 2026-07-21 — pin remaining private producer contracts and add Workflows authoring helpers

- **Class:** additive SDK change plus non-route contract refreshes.
- **Owner:** Contract Spine; producer behavior remains owned by Workflows,
  Cradle, Gym, and Tempera LLM.
- **Added:** `temperaWorkflows.composeWorkflow` and
  `temperaWorkflows.assistJson` in TypeScript, Python, and Rust. Both are
  non-running authoring helpers guarded by `workflow:write`; neither stores a
  workflow or executes a node.
- **Producer evidence:** exact committed locks now cover
  `tempera-dev/tempera-workflows@b135c6c72d3e67acd66be4c40ecec111350ed9e3`,
  `tempera-dev/cradle@daba206b8cab083d9ddf54a91cd95a7f98ac004f`,
  `tempera-dev/tempera-gym@7bac3b36085c6ba3a1f34ad793259fa54b9558de`,
  and
  `tempera-dev/tempera-llm@5c0b6d9bb026818540a55dc8946678e14485f771`.
  Each lock records the canonical path, Git blob, source SHA-256, generator,
  and generated artifact SHA-256.
- **Compatibility:** no producer route or schema was removed. Cradle adds
  egress receipt fields, Gym adds rollout request metadata, and Tempera LLM
  adds auth/security metadata to existing routes. Workflows adds two routes
  and their request/response schemas.
- **Migration:** no existing call changes. Consumers may adopt the new
  Workflows methods after upgrading.
- **Rollout:** release as aggregate SDK `0.8.0`; the four private source jobs,
  bidirectional strict drift gate, and all-language tests must execute before
  merge.
- **Rollback:** revert the SDK release without changing producer behavior; the
  prior `0.7.0` methods remain compatible with all unchanged routes.
- **Affected consumers:** aggregate TypeScript, Python, and Rust SDK users and
  the independently owned Workflows consumer surface.

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
