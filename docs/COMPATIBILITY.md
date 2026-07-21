# SDK compatibility ledger

## 2026-07-20 — Data Engine contract reconciliation

- Owner: Contract Spine (Lane 1).
- Compatibility class: breaking pre-1.0 SDK correction; package `0.7.0`, surface version `3`.
- Producer: `tempera-dev/data-engine@639c151012747e376938d1cfea71f7b2011b9116`, `api/openapi.yaml`.
- Consumers: TypeScript, Python, and Rust aggregate clients; Tempera Workflows' vendored SDK and Data Engine locks.
- Telemetry: none of the removed methods had a matching producer route, so successful calls could not have reached Data Engine. Consumer source search and Workflows lock checks replace route telemetry for this correction.
- Migration: replace removed calls only with an operation present in the committed Data Engine contract. The 12 newly generated methods below cover all previously omitted producer routes. Workflows must re-vendor the exact released SDK surface and Data Engine lock before this change merges.
- Rollback: revert the SDK release and consumer lock together; do not restore phantom routes to Data Engine.
- Removal evidence: bidirectional `sync-data-engine-openapi.py --check` reports 46 of 46 REST operations represented, with zero phantom and zero missing operations.

Removed phantom methods:

`archiveArtifact`, `cancelJob`, `cancelOperation`, `createConnector`, `createEval`,
`createLabel`, `createRepository`, `createTaskSet`, `createVerifier`,
`deleteConnector`, `deleteOperation`, `emitPreference`, `emitProduct`, `emitRlvr`,
`emitSft`, `enableDomain`, `expireArtifactRetention`, `generateDomain`,
`generateRepositoryTasks`, `getConnector`, `getDomain`, `getDomainPack`,
`getEnvironment`, `getEval`, `getLabel`, `getOperation`, `getRepository`,
`getRun`, `getTaskSet`, `getVerifier`, `listDomainPacks`, `listDomains`,
`listEnvironments`, `listEvals`, `listJobs`, `listLabels`, `listProducts`,
`listRepositories`, `listRuns`, `listTaskSetTasks`, `listTaskSets`,
`listVerifiers`, `patchArtifact`, `patchConnector`, `patchLabel`,
`patchRepository`, `patchVerifier`, `publishTaskSet`, `purgeArtifact`,
`runEnvironment`, `runEval`, `runVerifier`, `syncConnector`, and
`syncRepository`.

Added producer-backed methods:

`admitTrainingRelease`, `getTrainingRelease`, `createEvidenceRecord`,
`listEvidenceRecords`, `getEvidenceRecord`, `createEpisode`, `listEpisodes`,
`getEpisode`, `queryResearchRetrieval`, `createResearchCatalogEntry`,
`listResearchCatalogEntries`, and `getResearchCatalogEntry`.

Auth registration: Data Engine requires `training:publish` for training-release
admission and reads. Auth Hub registers that scope for the `data-engine`
audience at commit `03136c97be6ce5753e6a28abac88432773640d6f`; only attributed
owner/admin OAuth principals may receive it, and API keys are excluded. The SDK
therefore treats these operations as centrally reachable under that policy.

Canonical-source gap: the remaining Data Engine scope assignments in this
release are verified against `src/data_engine/app.py::_required_scope` at the
pinned producer commit, but `api/openapi.yaml` does not yet encode them as
machine-readable per-operation metadata. Data Engine issue
https://github.com/tempera-dev/data-engine/issues/38 owns making those auth
requirements contract-derived; this SDK correction must not be described as
fully OpenAPI-derived until that producer change lands and the lock is refreshed.

MCP exposure decision: this SDK release does not expand Data Engine's 36-tool
model-facing registry. Nine producer-backed REST operations—Episode,
EvidenceRecord, and ResearchCatalogEntry create/get/list—remain unexposed.
Data Engine issue https://github.com/tempera-dev/data-engine/issues/39 owns
turning those absences into explicit, scope/effect/schema-pinned admission
decisions; none should become a tool merely to mirror REST coverage.

Source verification: SDK CI uses the least-privilege Tempera Contract Reader
GitHub App to check out the private Data Engine repository at the lock's exact
commit and rerun the committed-source check. A merge requires that real-runner
job together with the aggregate SDK job; local checkout evidence alone is not
sufficient.

The same release also corrects the aggregate scope registry to Auth Hub main:
`memory:read`, `memory:write`, `memory:manage`, and `review:resolve` are added;
the unregistered `cyber:research` and `clinical:run` constants are removed.
Consumers using either removed constant must first land a reviewed Auth Hub
scope contract rather than asking the SDK to advertise an unissuable scope.

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
