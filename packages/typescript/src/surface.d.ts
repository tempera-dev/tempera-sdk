// GENERATED FROM surface.json by scripts/gen-sdk-surface.py -- DO NOT EDIT BY HAND.
// Type declarations for the generated surface tables plus the typed
// product-client interfaces used by createTemperaClient().

export type TemperaAudience = "palette" | "tempo" | "cradle" | "remi" | "human-data" | "data-engine" | "tempera-mcp" | "tempera-code";
export type TemperaScope = "mcp:invoke" | "trace:read" | "trace:write" | "dataset:read" | "dataset:write" | "eval:run" | "pii:unmask" | "cyber:research" | "clinical:run" | "model:read" | "model:invoke" | "admin";
export type TemperaEnvironment = "local" | "preview" | "staging" | "production";
export type TemperaProductKey = "controlPlane" | "palette" | "tempo" | "temperaCode" | "cradle" | "remi" | "dataEngine" | "humanData" | "tempJs" | "tempOS" | "arrha";

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
  mcpGatewayUrl: string;
  paletteApiUrl: string;
  paletteMcpUrl: string;
  publicSiteUrl: string;
  temperaCodeApiUrl: string;
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
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  auth: "none" | "account" | "product" | "introspectionSecret";
  pathParams: readonly string[];
  query: readonly string[];
  body: readonly string[];
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
  /** Check control-plane liveness; returns {ok: true}. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch OAuth 2.1 authorization-server metadata for the issuer. */
  discovery(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch the JSON Web Key Set used to verify control-plane access tokens. */
  jwks(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch OAuth protected-resource metadata for one registered audience. */
  protectedResourceMetadata(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a Tempera account (or accept an invite) and receive an account-session token pair. */
  signup(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Log in with email and password and receive an account-session token pair. */
  login(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch the authenticated user's identity, active workspace, and roles. */
  me(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Switch the active workspace and receive a token pair scoped to it. */
  selectWorkspace(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List the organizations the authenticated user belongs to. */
  listOrgs(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create an organization; the caller becomes its owner. */
  createOrg(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List projects across every organization the user belongs to. */
  listProjects(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a project in an organization (requires an org admin role). */
  createProject(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List environments across every project the user can access. */
  listEnvironments(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create an environment in a project (requires an org admin role). */
  createEnvironment(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List team members of the active organization. */
  listTeamMembers(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Change a team member's role (requires an org admin role; at least one owner must remain). */
  updateTeamMember(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Remove a team member from the active organization (idempotent). */
  removeTeamMember(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List invites for the active organization, newest first. */
  listInvites(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Invite a user to the active organization; the accept URL is returned once. */
  createInvite(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Cancel a pending invite (idempotent). */
  cancelInvite(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List API keys in the active workspace; secrets are never returned. */
  listApiKeys(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Mint a workspace API key (tp_...); the secret is returned exactly once. The workspace ids must match the token's workspace. */
  createApiKey(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Rotate an API key's secret; the new secret is returned exactly once. */
  rotateApiKey(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Revoke an API key (idempotent). */
  revokeApiKey(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List the OAuth grants the user has approved in the active workspace. */
  listGrants(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Revoke an OAuth grant and every refresh token issued under it. */
  revokeGrant(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List the user's active account sessions. */
  listSessions(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Revoke an account session and its tokens immediately (idempotent). */
  revokeSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List the connector catalog (MCP clients, editors, and API surfaces). */
  listConnectors(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch one connector's connection status for the active workspace. */
  getConnectorStatus(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List the product catalog with default scopes and setup paths. */
  listProducts(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch one product's activation status, entitlements, signals, and usage meters. */
  getProductStatus(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch the organization's plan, subscription, usage meters, entitlements, invoices, and pricing (requires a billing role). */
  getBillingStatus(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a checkout handoff URL for a plan on the chosen payment rail (requires a billing role). */
  createBillingCheckout(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch the billing-portal URL for the organization (requires a billing role). */
  getBillingPortal(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Record a usage event against a metered plan limit; requires a token carrying the meter's product scope and returns the updated meter. */
  recordUsage(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List recent audit-log events for the user and active organization (up to 50, newest first). */
  listAuditLog(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Introspect a token or tp_ API key server-side; requires the introspection secret and returns {active: false} for anything invalid. */
  introspectToken(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface PaletteClient extends TemperaProductClientBase {
  /** Check palette API liveness; returns {ok: true}. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List trace summaries for a tenant with filters and cursor pagination. */
  listTraces(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch one full trace with all canonical spans; unmasking PII requires the pii:unmask scope and a reason. */
  getTrace(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch one canonical span by trace and span id. */
  getSpan(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch a span's recorded input and output values. */
  getSpanIo(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Search spans by text query and facet filters. */
  searchSpans(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Ingest one native span; idempotent when an idempotency key is supplied. */
  ingestSpan(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Import spans from a named external source payload. */
  importSource(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Archive a trace to Parquet and return the archive manifest. */
  archiveTrace(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a dataset for curating cases from traces. */
  createDataset(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Promote a trace (or one span of it) into a dataset case. */
  promoteTraceToCase(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Snapshot a dataset into an immutable version for evals and experiments. */
  createDatasetVersion(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Mint a palette-scoped API key; the secret is returned exactly once. */
  createApiKey(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Revoke a palette API key. */
  revokeApiKey(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch usage totals for a tenant project. */
  getUsageSummary(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface TempoClient extends TemperaProductClientBase {
  /** Check tempod liveness; returns {ok: true}. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Check tempod readiness, including engine attachment, drain state, and session capacity. */
  ready(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch tempod's OpenAPI document, generated at runtime for this host. */
  openapi(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List browser sessions with their state and creation time. */
  listSessions(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Open a browser session at a URL; driverless sessions skip engine attachment. */
  createSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Close a browser session and release its engine resources. */
  closeSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch the session's compiled structured observation (ranked, stably-identified elements). */
  observe(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Apply a batch of semantic actions with policy gating; returns the applied diff or a policy decision. */
  actBatch(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Capture a PNG screenshot of the session, optionally annotated with set-of-marks. */
  screenshot(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch the session's event window after a sequence number. */
  sessionEvents(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Let a human surface take write ownership of the session and receive an adoption lease. */
  adoptSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Return write ownership of the session to the agent plane. */
  handoffSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Start an agent run against the session with a goal, action budget, and round limit. */
  createRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List agent runs, optionally filtered to one session. */
  listRuns(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch one agent run with its state. */
  getRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Cancel an agent run. */
  cancelRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Resume an agent run after a human handoff completes. */
  resumeRun(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Grant a pending policy confirmation and receive a single-use grant token. */
  grantConfirmation(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface TemperaCodeClient extends TemperaProductClientBase {
  /** Check Tempera Code gateway liveness. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List the entitled Tempera Code hosted model catalog. */
  listModels(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a non-streaming Responses-compatible inference request through the Tempera Code gateway. */
  createResponse(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface CradleClient extends TemperaProductClientBase {
  /** Check sandbox-daemon liveness; returns status, version, and uptime. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch the sandbox capability matrix: lanes, engines, limits, and integrations. */
  getCapabilities(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch the ecosystem integration contract this daemon implements. */
  getIntegrationContract(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Execute source synchronously in a sandbox lane and return the result with metrics. */
  execute(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Submit an asynchronous sandbox job; returns an operation handle to poll. */
  createJob(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch a sandbox job's status and result. */
  getJob(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Cancel a queued or running sandbox job (idempotent for already-cancelled jobs). */
  cancelJob(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch the browser sandbox profile levels and suppression modes this daemon offers. */
  getBrowserProfiles(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Request admission for a browser session at a sandbox level and receive the guard plan. */
  admitBrowserSession(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch the browser adapter contract, required controls, and conformance profile. */
  getBrowserAdapterContract(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
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
  /** Write one memory into the ledger and, by default, project it into the memory graph immediately. */
  remember(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Project pending ledger events into the memory graph and return the projection report. */
  project(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Run memory management over pending ledger events (same engine pass as project, tracked separately). */
  manage(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Answer a question from memory with evidence, citations, contradictions, and staleness signals. */
  query(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Run store maintenance: optimize, checkpoint, and optionally vacuum, repair orphans, and prune audit history. */
  maintenance(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export interface DataEngineClient extends TemperaProductClientBase {
  /** Check data-engine liveness; returns the service status. */
  health(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List installed versioned domain packs from data-engine's OpenAPI contract. */
  listDomainPacks(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get one installed versioned domain-pack manifest. */
  getDomainPack(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List immutable domain-pack bindings enabled for a project. */
  listDomains(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get one project-enabled, digest-pinned domain binding. */
  getDomain(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Enable an installed domain pack for a project; pass Idempotency-Key through the operation headers. */
  enableDomain(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Request bounded domain task generation with brokered model-profile and artifact references; the service reports unavailable until that worker and its Cradle lane are qualified. */
  generateDomain(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List installed descriptor-only environment definitions without claiming their execution lane is available. */
  listEnvironments(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get one installed environment descriptor. */
  getEnvironment(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get an asynchronous data-engine operation and its current terminal state. */
  getOperation(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Request cancellation of a running data-engine operation; pass Idempotency-Key through operation headers. */
  cancelOperation(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Delete a completed data-engine operation; pass Idempotency-Key through operation headers. */
  deleteOperation(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Register an approved domain-pack source connector; pass Idempotency-Key through operation headers. */
  createConnector(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List registered source connectors for a project. */
  listConnectors(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get a source connector and its current ETag. */
  getConnector(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Patch mutable connector settings; pass If-Match and Idempotency-Key through operation headers. */
  patchConnector(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Delete a connector registration; pass If-Match and Idempotency-Key through operation headers. */
  deleteConnector(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Start a bounded connector sync; pass Idempotency-Key through operation headers. */
  syncConnector(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Register a GitHub repository reference; pass Idempotency-Key through operation headers. */
  createRepository(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List registered project repositories. */
  listRepositories(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get one repository reference and its current ETag. */
  getRepository(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Patch mutable repository metadata; pass If-Match and Idempotency-Key through operation headers. */
  patchRepository(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Record a repository snapshot through the authenticated provider boundary; returns an operation. */
  syncRepository(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Request bounded repository task generation; service availability remains explicit until the approved github-evals worker gateway is configured. */
  generateRepositoryTasks(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Import an immutable worker-produced task set; pass Idempotency-Key through operation headers. */
  createTaskSet(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List repository task sets and publication state. */
  listTaskSets(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Get one immutable repository task set and its current ETag. */
  getTaskSet(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List structurally distinct evaluation and backlog tasks in a task set. */
  listTaskSetTasks(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Atomically publish explicitly selected qualified tasks; pass Idempotency-Key through operation headers. */
  publishTaskSet(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List the MVP use-case templates (data products and pipeline templates) for a project. */
  listUseCases(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch one MVP use-case template with its rubric, modalities, skill tags, and target accuracy. */
  getUseCase(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Ingest one artifact deterministically into the project; returns an async operation handle. */
  ingestArtifact(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch, parse, and ingest one public HTTP(S) page as a web artifact; returns an async operation handle. */
  ingestWeb(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Run a complete MVP use-case pipeline end to end; setting verifier to cradle selects sandboxed wasm verification. */
  runUseCase(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create a data campaign with a rubric, budget, target accuracy, and skill tags. */
  createCampaign(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List a project's data campaigns with pagination. */
  listCampaigns(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List a project's artifacts with filtering, ordering, and cursor pagination. */
  listArtifacts(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch one artifact, expanded to the requested view (BASIC or FULL). */
  getArtifact(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List the labels attached to one artifact. */
  listArtifactLabels(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Create an asynchronous labeling job over a set of artifacts; returns an operation handle to poll. */
  createJob(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch one labeling job with its state and progress. */
  getJob(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List the deterministic label results a job produced. */
  getJobResults(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** List the human residual review tasks queued for experts. */
  listExpertTasks(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch data-engine usage and quality metrics for a project. */
  getMetrics(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch public-site and ecosystem readiness signals for a project. */
  getEcosystemReadiness(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Emit an eval dataset bundle from verified artifacts; returns an async operation handle. */
  emitEval(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
  /** Fetch one emitted product bundle with its status and manifest URL. */
  getProduct(params?: TemperaOperationParams, options?: TemperaOperationOptions): Promise<unknown>;
}

export type PassthroughClient = TemperaProductClientBase;
