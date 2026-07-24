// GENERATED FROM surface.json by scripts/gen-sdk-surface.py -- DO NOT EDIT BY HAND.
// Type declarations for the generated surface tables plus the typed
// product-client interfaces used by createTemperaClient().

export type TemperaAudience = "palette" | "tempo" | "cradle" | "remi" | "human-data" | "data-engine" | "tempera-mcp" | "tempera-code" | "tempera-llm" | "tempera-workflows" | "tempera-gym" | "tempera-bio";
export type TemperaScope = "mcp:invoke" | "memory:read" | "memory:write" | "memory:manage" | "trace:read" | "trace:write" | "dataset:read" | "dataset:write" | "eval:run" | "training:publish" | "review:gold:manage" | "review:resolve" | "workflow:read" | "workflow:write" | "workflow:run" | "bio:source:read" | "bio:proposal:write" | "bio:measurement:verify" | "bio:decision:write" | "bio:experiment:approve" | "bio:experiment:submit" | "bio:signer:manage" | "model:read" | "model:invoke" | "usage:reserve" | "pii:unmask" | "admin";
export type TemperaEnvironment = "local" | "preview" | "staging" | "production";
export type TemperaProductKey = "controlPlane" | "palette" | "tempo" | "temperaLlm" | "temperaWorkflows" | "temperaGym" | "temperaBio" | "cradle" | "remi" | "dataEngine" | "humanData" | "tempJs" | "tempOS" | "arrha";

export declare const TEMPERA_SURFACE_VERSION: number;
export declare const TEMPERA_AUDIENCES: readonly TemperaAudience[];
export declare const DEFAULT_AUDIENCE: "palette";
export declare const TEMPERA_SCOPES: readonly TemperaScope[];

export type TemperaIssuerPaths = {
  authorize: string;
  token: string;
  revoke: string;
  introspect: string;
  mcp: string;
};
export declare const TEMPERA_ISSUER_PATHS: Readonly<TemperaIssuerPaths>;

export type TemperaEnvironmentTargets = {
  authIssuerUrl: string;
  authJwksUrl: string;
  controlPlaneUrl: string;
  cradleApiUrl: string;
  dataEngineApiUrl: string;
  mcpGatewayUrl: string;
  paletteApiUrl: string;
  paletteMcpUrl: string;
  publicSiteUrl: string;
  temperaGymUrl: string;
  temperaLlmApiUrl: string;
  temperaWorkflowsApiUrl: string;
  tempoApiUrl: string;
};
export declare const TEMPERA_ENVIRONMENTS: Readonly<Record<TemperaEnvironment, TemperaEnvironmentTargets>>;

export type TemperaProduct = {
  name: string;
  repository: string;
  envVar: string;
  audience: TemperaAudience | null;
  description: string;
};
export declare const TEMPERA_PRODUCTS: Readonly<Record<TemperaProductKey, TemperaProduct>>;

export type TemperaOperationSpec = {
  id: string;
  upstreamOperationId: string;
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  auth: "none" | "account" | "product" | "oauthResource" | "introspectionSecret";
  authAudience: TemperaAudience | null;
  pathParams: readonly string[];
  pathParamTemplates: Readonly<Record<string, string>>;
  query: readonly string[];
  body: readonly string[];
  forbiddenBody: readonly string[];
  requiredBody: readonly string[];
  bodyDefaults: Readonly<Record<string, unknown>>;
  scope: TemperaScope | null;
  description: string;
};
export declare const TEMPERA_OPERATIONS: Readonly<Record<TemperaProductKey, readonly TemperaOperationSpec[]>>;

export type TemperaMcpMethodSpec = { id: string; rpc: string; tool?: string; description: string };
export declare const TEMPERA_MCP_GATEWAY: Readonly<{
  description: string;
  methods: readonly TemperaMcpMethodSpec[];
  errorCodes: Readonly<Record<string, number>>;
}>;

export type TemperaOperationParams = Record<string, unknown>;
export type TemperaOperationOptions = { headers?: Record<string, string>; bearer?: string };
export type TemperaPassthroughOptions = {
  method?: string;
  body?: unknown;
  query?: Record<string, unknown>;
  headers?: Record<string, string>;
  bearer?: string;
};

export type TemperaProductClientBase = TemperaProduct & {
  key: TemperaProductKey;
  /** Passthrough request for endpoints the surface tables do not cover yet. */
  request(path: string, options?: TemperaPassthroughOptions): Promise<unknown>;
};

export interface ControlPlaneClient extends TemperaProductClientBase {
  /** Liveness probe for the control plane. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Readiness probe for durable control-plane storage. */
  getReadiness(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Return the current authenticated principal and active workspace context. */
  me(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List organizations/workspaces visible to the current user. */
  listOrgs(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create an organization/workspace. */
  createOrg(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List active account-console sessions for the current user. */
  listSessions(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a first-party hosted account session from email/password login or signup. */
  createHostedSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Revoke an account-console session and its refresh token. Revoking an unknown session id is a no-op. */
  revokeSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Select the active organization, project, and environment for the account console. */
  selectWorkspace(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List team members for the active organization. */
  listTeamMembers(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Update a team member role. */
  updateTeamMember(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Remove a team member from the active organization. */
  removeTeamMember(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List organization invites. */
  listInvites(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Invite a teammate to the active organization. */
  createInvite(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Cancel an organization invite. */
  cancelInvite(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List projects for the active organization. */
  listProjects(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a project in the active organization. */
  createProject(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List environments for the active project. */
  listEnvironments(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create an environment in a project owned by the active organization. */
  createEnvironment(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List scoped API keys for the active workspace. Plaintext key material is never returned. */
  listApiKeys(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a scoped API key. Plaintext key material is returned once. */
  createApiKey(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Revoke a scoped API key. Revoking an unknown key id is a no-op. */
  revokeApiKey(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Rotate a scoped API key. New plaintext key material is returned once. */
  rotateApiKey(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List provider connection metadata using a first-party account session. Secret references and values are never returned. */
  providerConnectionsList(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a tenant-scoped provider connection using only an external secret reference. */
  providerConnectionsCreate(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Revoke a provider connection immediately. Revoking an unknown id is a no-op. */
  providerConnectionsRevoke(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Replace a connection secret reference and increment its revision without exposing the reference. */
  providerConnectionsRotate(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Resolve connection runtime metadata for a tenant-bound tempera-llm service credential. */
  providerConnectionsResolve(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List external experiment-provider metadata. Secret references and values are never returned. */
  listExperimentProviderConnections(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Register a tenant-scoped experiment provider using only an external secret reference. */
  createExperimentProviderConnection(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Revoke an experiment-provider connection. An unknown id is a no-op. */
  revokeExperimentProviderConnection(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Atomically consume an exact human approval and resolve a provider reference for tempera-workflows. */
  resolveExperimentProviderConnection(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List versioned public Ed25519 verifier keys for an authorized human administrator. */
  listBioSignerKeys(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Register or rotate a public Ed25519 verifier key. Private key material is rejected. */
  createBioSignerKey(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Revoke a public verifier key while retaining its history. */
  revokeBioSignerKey(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List exact, single-use experiment approvals for an authorized human approver. */
  listExperimentApprovals(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a short-lived human approval bound to exact proposal, protocol, provider, and MCP preparation digests. */
  createExperimentApproval(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Revoke an unused experiment approval. Consumed approvals remain immutable. */
  revokeExperimentApproval(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List recent scoped account and security activity for the active user and organization. */
  listAuditLog(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List supported hosted connectors and their setup metadata. */
  listConnectors(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Return connection status for one connector. */
  getConnectorStatus(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List registered Tempera products and their setup metadata. */
  listProducts(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Return entitlement and first-mile setup status for one product. */
  getProductStatus(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Return billing plan, usage, entitlement, customer, and invoice state for owner, admin, or billing users. */
  getBillingStatus(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a Stripe checkout, fiat invoice, or crypto settlement handoff URL. */
  createBillingCheckout(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a customer billing portal handoff URL. */
  getBillingPortal(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Return the org credit wallet balance, grant, overage, and recent ledger for owner, admin, or billing users. Internal cost/margin fields are redacted from the ledger for non-staff callers and returned in full only to platform staff. */
  getBillingCredits(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List the entitled Tempera Code model catalog. Requires model:read. */
  getModelCatalog(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Report a billable usage event and receive the current entitlement decision. */
  recordUsage(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Atomically reserve the maximum model cost before starting a provider request. */
  usageReservationsCreate(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Commit exact provider usage against an admitted reservation and release unused capacity. */
  usageReservationsCommit(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Release unused capacity after provider failure or cancellation. */
  usageReservationsRelease(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Hold maximum capacity and record non-secret evidence when exact provider usage is unavailable. */
  usageReservationsReconcile(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List connected OAuth app grants for the active workspace. */
  listGrants(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Revoke an OAuth app grant and its refresh tokens. */
  revokeGrant(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Validate a central access token or hosted API key for resource servers. */
  introspectToken(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** OAuth authorization server discovery metadata. */
  discovery(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** OAuth protected resource discovery metadata for MCP/resource clients. */
  getOAuthProtectedResourceMetadata(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** OAuth protected resource discovery metadata for one registered resource audience. */
  protectedResourceMetadata(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** JSON Web Key Set for validating central issuer JWTs. */
  jwks(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Return fail-closed source, machine, and image provenance for the serving runtime to a platform-staff account session. */
  adminOperationalProvenance(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Re-authenticate a platform-staff account session to mint a short-lived step-up elevation required for sensitive admin mutations. */
  adminStepUp(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Platform-staff credit grant/adjustment to an org wallet. Requires a fresh step-up elevation; idempotent on the reference. */
  adminAdjustCredits(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Platform-staff internal billing view: per-org wallet balances plus provider cost, customer charge, and margin economics. */
  adminBillingOrgs(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a one-time CSRF-bound GitHub App installation session. */
  githubSetupSessionsCreate(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Bind a GitHub installation callback to its authenticated workspace. */
  githubSetupSessionsComplete(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List active GitHub App installations for the organization. */
  githubInstallationsList(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Disconnect a GitHub App installation from the workspace. */
  githubInstallationsDisconnect(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List repository metadata received for a GitHub installation. */
  githubInstallationRepositoriesList(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Capture an ephemeral, immutable GitHub repository snapshot for an authorized workspace. */
  githubRepositorySnapshotsCapture(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Accept a signed, replay-deduplicated GitHub webhook. */
  githubWebhooksAccept(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface PaletteClient extends TemperaProductClientBase {
  /** Call GET /health. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/alerts/{tenantId}/{projectId}/traces/{traceId}/webhook. */
  alertsEvaluate(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/api-keys/{tenantId}/{projectId}/{environmentId}. */
  createApiKey(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/api-keys/{tenantId}/{projectId}/{environmentId}/{apiKeyId}/revoke. */
  revokeApiKey(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/archive/{tenantId}/{projectId}/spans. */
  archiveQuerySpans(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/archive/{tenantId}/{projectId}/{traceId}. */
  archiveTrace(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/audit/{tenantId}/{projectId}. */
  auditList(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/calibrations/{tenantId}/{projectId}/{datasetId}/versions/{versionId}. */
  calibrationsRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/connect/status/{tenantId}/{projectId}. */
  connectGetStatus(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/connectors/{tenantId}/{projectId}. */
  connectorsList(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/connectors/{tenantId}/{projectId}/connect. */
  connectorsConnect(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/connectors/{tenantId}/{projectId}/invoke. */
  connectorsInvokeTool(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/connectors/{tenantId}/{projectId}/skills. */
  connectorsGetSkills(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/connectors/{tenantId}/{projectId}/status. */
  connectorsStatus(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/connectors/{tenantId}/{projectId}/tools. */
  connectorsListTools(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/datasets/{tenantId}/{projectId}. */
  createDataset(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/datasets/{tenantId}/{projectId}/{datasetId}/cases/from-trace. */
  promoteTraceToCase(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/datasets/{tenantId}/{projectId}/{datasetId}/versions. */
  createDatasetVersion(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/datasets/{tenantId}/{projectId}/{datasetId}/versions/{versionId}/evals/deterministic. */
  evalsRunDeterministic(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/datasets/{tenantId}/{projectId}/{datasetId}/versions/{versionId}/evals/judge. */
  evalsRunJudge(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/eval-results/{tenantId}/{projectId}/tempera/bundles. */
  importTemperaBundle(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/eval-results/{tenantId}/{projectId}/tempera/decisions. */
  recordTemperaDecision(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/eval-results/{tenantId}/{projectId}/tempera/{kind}/{externalId}. */
  getTemperaEvidence(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/experiments/{tenantId}/{projectId}/{datasetId}/versions/{versionId}/deterministic. */
  experimentsRunDeterministic(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/experiments/{tenantId}/{projectId}/{datasetId}/versions/{versionId}/judge. */
  experimentsRunJudge(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/gates/{tenantId}/{projectId}. */
  gatesCreate(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/gates/{tenantId}/{projectId}/{gateId}/run. */
  gatesRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/import/{tenantId}/{projectId}/{environmentId}. */
  importSource(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/ingest/{tenantId}/{projectId}/dead-letters/{messageId}/replay. */
  ingestReplayDeadLetter(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/ingest/{tenantId}/{projectId}/queue. */
  ingestGetQueueStatus(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/ingest/{tenantId}/{projectId}/trace-ingested/drain. */
  ingestDrainTraceIngested(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/ingest/{tenantId}/{projectId}/trace-writes/drain. */
  ingestDrainTraceWrites(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/ingest/{tenantId}/{projectId}/traces/{traceId}/reconcile. */
  ingestReconcileTrace(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/judge/{tenantId}/{projectId}/evaluate. */
  judgeEvaluate(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/judge/{tenantId}/{projectId}/ledger. */
  judgeListLedger(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/online/{tenantId}/{projectId}/traces/{traceId}/sampling. */
  onlineDecideSampling(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/prompts/{tenantId}/{projectId}. */
  promptsList(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/prompts/{tenantId}/{projectId}. */
  promptsCreate(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/prompts/{tenantId}/{projectId}/{promptId}. */
  promptsGet(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/prompts/{tenantId}/{projectId}/{promptId}/diff. */
  promptsDiffVersions(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/prompts/{tenantId}/{projectId}/{promptId}/versions. */
  promptsListVersions(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/prompts/{tenantId}/{projectId}/{promptId}/versions. */
  promptsAddVersion(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/provider-secrets/{tenantId}/{projectId}. */
  providerSecretsList(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/provider-secrets/{tenantId}/{projectId}. */
  providerSecretsCreate(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/provider-secrets/{tenantId}/{projectId}/{providerSecretId}/revoke. */
  providerSecretsRevoke(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/review-queues/{tenantId}/{projectId}. */
  reviewsCreateQueue(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/review-queues/{tenantId}/{projectId}/{queueId}/tasks. */
  reviewsListTasks(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/review-queues/{tenantId}/{projectId}/{queueId}/tasks/from-trace. */
  reviewsEnqueueTaskFromTrace(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/review-queues/{tenantId}/{projectId}/{queueId}/tasks/{taskId}/annotations. */
  reviewsSubmitAnnotation(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/review-queues/{tenantId}/{projectId}/{queueId}/tasks/{taskId}/annotations/{annotationId}/promote. */
  reviewsPromoteAnnotation(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/scenarios/{tenantId}/{projectId}. */
  scenariosList(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/scenarios/{tenantId}/{projectId}. */
  scenariosCreate(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/scenarios/{tenantId}/{projectId}/mine. */
  scenariosMine(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/scenarios/{tenantId}/{projectId}/{scenarioId}. */
  scenariosGet(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/search/{tenantId}/spans. */
  searchSpans(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/spans/{tenantId}/{traceId}/{spanId}. */
  getSpan(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/spans/{tenantId}/{traceId}/{spanId}/io. */
  getSpanIo(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/traces/native. */
  ingestSpan(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/traces/{tenantId}. */
  listTraces(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/traces/{tenantId}/{traceId}. */
  getTrace(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/usage/{tenantId}/{projectId}. */
  getUsageSummary(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface TempoClient extends TemperaProductClientBase {
  /** Call GET /.well-known/agent-card.json. */
  agentCard(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /.well-known/agent.json. */
  agentJson(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /health. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /metrics. */
  metrics(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /openapi.json. */
  openapi(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /ready. */
  ready(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/drain. */
  drain(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/runs. */
  listRuns(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/runs/{runId}. */
  getRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/runs/{runId}/events. */
  runEvents(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/runs/{runId}:cancel. */
  cancelRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/runs/{runId}:resume. */
  resumeRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/sessions. */
  listSessions(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/sessions. */
  createSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call DELETE /v1/sessions/{sessionId}. */
  closeSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/sessions/{sessionId}/confirmations/{confirmationId}:grant. */
  grantConfirmation(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/sessions/{sessionId}/events. */
  sessionEvents(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/sessions/{sessionId}/manager. */
  managerSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/sessions/{sessionId}/runs. */
  createRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/sessions/{sessionId}/surfaces. */
  registerSessionSurface(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call DELETE /v1/sessions/{sessionId}/surfaces/{surfaceId}. */
  removeSessionSurface(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/sessions/{sessionId}:actBatch. */
  actBatch(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/sessions/{sessionId}:adopt. */
  adoptSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/sessions/{sessionId}:handoff. */
  handoffSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/sessions/{sessionId}:observe. */
  observe(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/sessions/{sessionId}:screenshot. */
  screenshot(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/sessions/{sessionId}:transform. */
  transformSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface TemperaLlmClient extends TemperaProductClientBase {
  /** Call GET /healthz. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /readyz. */
  readinessCheck(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/chat/completions. */
  createChatCompletion(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/models. */
  listModels(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/responses. */
  createResponse(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface TemperaWorkflowsClient extends TemperaProductClientBase {
  /** Liveness. Unauthenticated. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** The studio palette: every node type with config JSON Schema and outputs. */
  listNodeTypes(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List runs, newest first. */
  listRuns(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Full run view: status, per-node states with outputs/logs/metrics, timestamps. */
  getRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Cancel a queued, running, or waiting run. Already-cancelled runs return 200. */
  cancelRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Consume a durable external callback and resume a waiting run. */
  runsSignal(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List workflows. */
  listWorkflows(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a workflow from a `tempera.workflow/v1` definition. */
  createWorkflow(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Delete a workflow. Existing runs keep their definition snapshots. */
  deleteWorkflow(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get one workflow. */
  getWorkflow(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Replace a workflow definition through an AIP-style masked update. */
  updateWorkflow(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Start a run (job pattern): returns immediately with the queued run; poll. */
  createRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a run AND wait for it to finish, returning the run + output in one. */
  callWorkflow(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Compile a validated, unsaved, bounded Bio campaign workflow draft. */
  compileBioCampaign(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Ask Tempera Code to propose a validated workflow draft, or search the full. */
  composeWorkflow(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Generate or repair one JSON configuration value with the configured. */
  assistJson(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Validate a definition without saving it. Returns 200 with the issue list. */
  validateWorkflow(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface TemperaGymClient extends TemperaProductClientBase {
  /** Liveness probe (unauthenticated). */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Built-in and boot-trusted versioned environment catalog. */
  listEnvironments(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Domain capabilities represented in the versioned task catalog. */
  listDomains(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List versioned task definitions without agent inputs. */
  listTasks(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get one immutable task definition including its agent-visible input. */
  getTask(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Deterministically verify one candidate without creating an episode. */
  evaluateTask(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List verifier identities and bound tasks without grader content. */
  listVerifiers(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List durable episode snapshots, newest first. */
  listEpisodes(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Reset a versioned task into a durable episode. */
  createEpisode(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Read and content-verify one durable episode snapshot. */
  getEpisode(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Apply one schema-validated action and persist the transition. */
  stepEpisode(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Retain a completed Gym episode and trajectory in Data Engine. */
  exportEpisode(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Persisted-run index, newest first. */
  listRuns(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Full trajectory envelope (incl. metadata.timing) for one run. */
  getRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Execute one rollout synchronously, store it, return the summary. */
  createRollout(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Discover boot-trusted exact sealed-evaluator identities. */
  listSealedEvaluators(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List persisted sealed-evaluation precommits and results. */
  listSealedEvaluations(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Persist an opaque sealed-suite commitment before policy freeze. */
  precommitSealedEvaluation(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Read one verified precommit and aggregate sealed result. */
  getSealedEvaluation(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Evaluate one frozen policy through its exact sealed adapter. */
  runSealedEvaluation(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface TemperaBioClient extends TemperaProductClientBase {
  /** Derive campaign state. */
  deriveCampaignState(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Prepare candidate set. */
  prepareCandidateSet(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Prepare dataset release manifest. */
  prepareDatasetReleaseManifest(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Derive decision. */
  deriveDecision(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Prepare experiment proposal. */
  prepareExperimentProposal(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Prepare hypothesis. */
  prepareHypothesis(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Verify measurement. */
  verifyMeasurement(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Prepare program. */
  prepareProgram(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Ingest mave d b score set. */
  ingestMaveDBScoreSet(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface CradleClient extends TemperaProductClientBase {
  /** Call POST /v1/browser/adapter/capability. */
  projectsBrowserAdaptersIssueCapability(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/browser/adapter/completion/validate. */
  projectsBrowserAdaptersValidateCompletion(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/browser/adapter/contract. */
  getBrowserAdapterContract(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/browser/adapter/launch/claim. */
  projectsBrowserAdaptersClaimLaunch(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/browser/adapter/launch/plan. */
  projectsBrowserAdaptersPlanLaunch(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/browser/adapter/register. */
  projectsBrowserAdaptersRegister(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/browser/adapter/validate. */
  projectsBrowserAdaptersValidate(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/browser/admit. */
  admitBrowserSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/browser/profiles. */
  getBrowserProfiles(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/capabilities. */
  getCapabilities(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/execute. */
  execute(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/health. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/integration. */
  getIntegrationContract(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/jobs. */
  createJob(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call DELETE /v1/jobs/{id}. */
  cancelJob(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/jobs/{id}. */
  getJob(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call POST /v1/projects/{project}/modules. */
  projectsModulesCreate(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Call GET /v1/projects/{project}/modules/{sha256}. */
  projectsModulesGet(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface RemiClient extends TemperaProductClientBase {
  /** Check memory-server liveness. */
  livez(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Check memory-server readiness, including database health. */
  readyz(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch deep store health: schema version, integrity checks, and graph consistency. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch memory-store statistics: ledger events, nodes, and token counts by kind. */
  getStats(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch service metrics as JSON, including per-route counters and query-tier latencies. */
  getMetrics(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch service metrics in Prometheus text exposition format for scrape-based monitoring. */
  getPrometheusMetrics(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List recent service audit events (default 100, maximum 500). */
  listAudit(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Write one memory event into the tenant and project ledger. */
  remember(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Project pending ledger events into the memory graph and return the projection report. */
  project(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Answer a scoped memory question with evidence and reconstruction metadata. */
  query(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Run store maintenance: optimize, checkpoint, and optionally vacuum, repair orphans, and prune audit history. */
  maintenance(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface DataEngineClient extends TemperaProductClientBase {
  /** Health check. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List MVP data products and pipeline templates. */
  listUseCases(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get one MVP use-case template. */
  getUseCase(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Ingest one or many artifacts. */
  ingestArtifact(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch, parse, and ingest a public HTTP/HTTPS page. */
  ingestWeb(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a data campaign with rubric, budget, target accuracy, and skill tags. */
  createCampaign(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List data campaigns. */
  listCampaigns(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Pause, resume, or permanently close campaign job admission. */
  transitionCampaign(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get the authenticated reviewer's campaign qualification. */
  getReviewerQualification(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Run a complete MVP use-case pipeline. */
  runUseCase(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List human residual review tasks. */
  listExpertTasks(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Clone a real review task into an isolated HMAC-scored qualification task. */
  createReviewQualificationTask(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Resolve, abstain, flag, or adjudicate one human residual. */
  resolveExpertTask(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Atomically claim one open expert task with an exclusive renewable lease. */
  claimExpertTask(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Renew the authenticated reviewer's active task lease. */
  renewExpertTaskAssignment(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Release the authenticated reviewer's active task lease for reassignment. */
  releaseExpertTaskAssignment(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Autosave a version-checked draft under the active reviewer lease. */
  saveExpertTaskDraft(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get project-scoped human-review operations and quality measures. */
  getReviewOperations(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get data-engine usage and quality metrics for a project. */
  getMetrics(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get the label quality report for a project. */
  getLabelQuality(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get public-site and ecosystem readiness for one project. */
  getEcosystemReadiness(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List artifacts. */
  listArtifacts(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get an artifact. */
  getArtifact(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List labels for an artifact. */
  listArtifactLabels(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Profile dataset quality before export. */
  profileDataset(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a labeling job. */
  createJob(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get a job. */
  getJob(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List deterministic results for a job. */
  getJobResults(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get product. */
  getProduct(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Validate an emitted product bundle. */
  validateProduct(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Check raw_hash leakage between two product bundles. */
  checkProductLeakage(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get an integrity-checked eval product manifest. */
  getProductManifest(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Admit an exact product generation for model training. */
  admitTrainingRelease(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Revalidate and get a training release. */
  getTrainingRelease(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Derive a post-training bundle (SFT or preference) from a READY product. */
  deriveBundle(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Emit eval bundle. */
  emitEval(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Extract from a source connector (s3, snowflake, salesforce) into artifacts. */
  extractSource(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List source connectors with configured/unconfigured state. */
  listConnectors(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create or version-bump a stored custom tool. */
  createTool(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List stored custom tools with usage stats. */
  listTools(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get a stored custom tool (definition + stats). */
  getTool(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Hard-delete a stored custom tool. */
  deleteTool(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Invoke a stored custom tool. */
  invokeTool(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Atomically commit an immutable discovery release graph. */
  commitDiscoveryRelease(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get one immutable discovery release. */
  getDiscoveryRelease(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create an immutable shared evidence record. */
  createEvidenceRecord(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List immutable shared evidence records. */
  listEvidenceRecords(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get one immutable shared evidence record. */
  getEvidenceRecord(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create an immutable shared episode. */
  createEpisode(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List immutable shared episodes. */
  listEpisodes(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get one immutable shared episode. */
  getEpisode(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Retrieve candidates for an exact canonical typed obligation. */
  queryResearchRetrieval(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create an immutable executable research catalog entry. */
  createResearchCatalogEntry(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List immutable executable research catalog entries. */
  listResearchCatalogEntries(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get one immutable executable research catalog entry. */
  getResearchCatalogEntry(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface HumanDataClient extends TemperaProductClientBase {
  /** Compute live qualification evidence. */
  computeQualification(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export type PassthroughClient = TemperaProductClientBase;
