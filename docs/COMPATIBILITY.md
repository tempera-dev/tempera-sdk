# SDK compatibility ledger

## 2026-07-24 — org-wide current-head contract convergence

- Owner: Contract Spine across the current producer default branches.
- Compatibility class: breaking pre-1.0 correction; package `0.11.0`, surface version `5`.
- Producers: Data Engine, Auth Hub, Palette, Cradle, Tempera Gym, Tempera Bio,
  Human Data, Tempera LLM, Tempera Workflows, Remi, and Tempo are pinned to
  exact reviewed source commits. Each adjacent source receipt records the
  authoritative repository, `main` branch, path, commit, and content hashes.
- Coverage: every ordinary buffered HTTP operation that the aggregate
  transport can represent is generated in TypeScript, Python, and Rust. OTLP, OAuth
  form/redirect, inbound webhook, MCP JSON-RPC, private Fabric, BiDi/WebSocket,
  and SSE routes remain explicit reviewed transport exclusions.
- Breaking corrections: Auth Hub's duplicate `signup`/`login` aliases become
  the canonical `createHostedSession` operation; Data Engine adopts its
  canonical `/v1/{parent}` paths and current request fields. Its
  `projects/*` resource-name template is validated and expanded without
  percent-encoding the canonical slash in all three languages. Tempera Bio and
  Human Data gain generated typed clients from their committed producer
  contracts. Workflows retains its durable run-signal client from current
  `main`. The fictitious
  Tempera Code HTTP gateway methods are removed because its public protocol is
  generated JSON-RPC, not `/v1/models` or `/v1/responses`. Remi is repinned
  from a stale feature branch to its committed `main` manifest; `manage`,
  `context`, and `feedback` are removed because current main does not route
  them, while `remember` and `query` regain their actual explicit workspace
  fields.
- Enforcement: source locks must equal the fetched producer branch head,
  generated surface bindings and producer `operationId` receipts must reproduce
  from the vendored contracts, transport exclusions expire for review, and
  warning-tier coverage migrations are removed. The executable Google Cloud AIP
  ratchet rejects path-version, PUT, parameter-casing, JSON-field-casing,
  custom-verb-casing, pagination, update-mask, and standard-error violations;
  all eight mechanical categories are at zero. Full AIP-122 and AIP-131 through
  AIP-136 resource-family redesign, plus AIP-151/AIP-155 long-running-operation
  semantics, remain explicit producer-owned breaking work rather than being
  mislabeled as complete. Hosted exact-source jobs reproduce installed private
  producer contracts at their recorded commits. Bio, Remi, and Tempo retain
  expiring, commit-bound gap receipts until the least-privilege Contract Reader
  app is installed on those repositories; their producer-side checks and local
  exact-source reproduction remain required in the interim.
- Rollback: revert the SDK release and all dependent exact-SHA pins together;
  do not restore phantom routes or weaken current-head drift checks.

## 2026-07-21 — Data Engine review qualification v1

- Owner: Contract Spine (Lane 1) consuming the Lane 2 producer contract.
- Compatibility class: additive SDK surface and exact-source refresh.
- Producer: `tempera-dev/data-engine@1ac9a5cccc5e087fefbfeed4b8e7b21c82751578`.
- Authority: `tempera-dev/auth-hub@f7c2815bc02d642e14f31295242964eb2e3a5c07`
  registers `review:gold:manage` for Data Engine owner/admin OAuth principals
  and excludes it from API keys.
- Auth refresh note: the exact current control-plane contract also adds the
  staff-only `adminOperationalProvenance` route. It remains deliberately
  upstream-only rather than becoming a general aggregate SDK method; the
  count-pinned migration classification advances from 23 to 24.
- Added: `createReviewQualificationTask` under `review:gold:manage` and
  `getReviewerQualification` under `review:resolve`, in TypeScript, Python, and
  Rust. The create request preserves the producer's write-only
  `expected_label`; the read is caller-bound and excludes blind-probe results.
- MCP: both operations remain explicitly REST-only. The producer admission
  catalog now records 52 authenticated operations as 36 exposed and 16 denied;
  the SDK check derives total coverage from the exact OpenAPI instead of a stale
  fixed count.
- Migration: none; existing methods and routes are unchanged.
- Rollout: regenerate and test all three clients, then re-vendor the exact SDK
  and Data Engine locks in Workflows and the exact Data Engine catalog in MCP.
- Rollback: revert the SDK and downstream consumer locks together; do not remove
  the producer operations.

## 2026-07-20 — Data Engine contract reconciliation

- Owner: Contract Spine (Lane 1).
- Compatibility class: breaking pre-1.0 SDK correction; package `0.9.0`, surface version `3`.
- Producer: `tempera-dev/data-engine@6357839770bdb2d586915d4d1c14066fd77840b8`, `api/openapi.yaml`, `api/mcp-admission.json`, and `api/mcp-tools.json`.
- Consumers: TypeScript, Python, and Rust aggregate clients; Tempera Workflows' vendored SDK and Data Engine locks.
- Telemetry: none of the removed methods had a matching producer route, so successful calls could not have reached Data Engine. Consumer source search and Workflows lock checks replace route telemetry for this correction.
- Migration: replace removed calls only with an operation present in the committed Data Engine contract. The 12 reconciliation methods, four assignment-lifecycle methods, and review-operations snapshot below cover all previously omitted producer routes. Workflows must re-vendor the exact released SDK surface and Data Engine locks before this change merges.
- Rollback: revert the SDK release and consumer lock together; do not restore phantom routes to Data Engine.
- Removal evidence: bidirectional `sync-data-engine-openapi.py --check` reports 51 of 51 REST operations represented, with zero phantom and zero missing operations.

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

Producer additions incorporated after the initial reconciliation:

`claimExpertTask`, `renewExpertTaskAssignment`, `releaseExpertTaskAssignment`,
and `saveExpertTaskDraft`. `resolveExpertTask` also accepts the producer's
optional `lease_token`. All five assignment-aware calls use the existing
`review:resolve` scope enforced by the Data Engine runtime.

`getReviewOperations` adds the producer's bounded, read-only human-review
operations snapshot. It uses the canonical `review:resolve` scope and does not
mutate, promote, or expose review decisions to models.

Auth registration: Data Engine requires `training:publish` for training-release
admission and reads. Auth Hub registers that scope for the `data-engine`
audience at commit `03136c97be6ce5753e6a28abac88432773640d6f`; only attributed
owner/admin OAuth principals may receive it, and API keys are excluded. The SDK
therefore treats these operations as centrally reachable under that policy.

Canonical auth source: every Data Engine OpenAPI operation now carries explicit
`x-tempera-audience` and `x-tempera-required-scope` metadata, runtime-checked by
the producer. The SDK operation lock stores those fields and the SDK gate
compares every generated operation's auth mode and scope in both directions.

MCP exposure decision: this SDK release does not expand Data Engine's 36-tool
model-facing registry. Fourteen producer-backed REST operations—Episode,
EvidenceRecord, and ResearchCatalogEntry create/get/list, the four
assignment-lifecycle operations, and `getReviewOperations`—have explicit deny
records. The vendored producer admission and tools artifacts bind exact scope,
effect, guard, idempotency, and schema-fixture evidence for all 50 authenticated
project operations. None becomes a tool merely to mirror REST coverage.

Source verification: SDK CI uses the least-privilege Tempera Contract Reader
GitHub App to check out the private Data Engine repository at the locks' shared
exact commit and reproduce the OpenAPI auth/operation lock plus both MCP
artifacts. A merge requires that real-runner job together with the aggregate SDK
job; local checkout evidence alone is not sufficient.

The same release also corrects the aggregate scope registry to Auth Hub main:
`memory:read`, `memory:write`, `memory:manage`, and `review:resolve` are added;
the unregistered `cyber:research` and `clinical:run` constants are removed.
Consumers using either removed constant must first land a reviewed Auth Hub
scope contract rather than asking the SDK to advertise an unissuable scope.
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
