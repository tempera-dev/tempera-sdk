# Compatibility ledger

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

Known auth gap: Data Engine requires `training:publish` for training-release
admission and reads, but Auth Hub does not register that scope on its current
default branch. The SDK records the requirement and marks these operations as
centrally unavailable until the Hosted Platform owner lands the Auth Hub scope.

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

The same release also corrects the aggregate scope registry to Auth Hub main:
`memory:read`, `memory:write`, `memory:manage`, and `review:resolve` are added;
the unregistered `cyber:research` and `clinical:run` constants are removed.
Consumers using either removed constant must first land a reviewed Auth Hub
scope contract rather than asking the SDK to advertise an unissuable scope.
