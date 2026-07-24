// GENERATED FROM surface.json by scripts/gen-sdk-surface.py -- DO NOT EDIT BY HAND.
// The SDK surface tables: products, audiences, scopes, environments,
// the error contract, and every typed operation, shared verbatim with
// the Python and Rust packages.

export const TEMPERA_SURFACE_VERSION = 4;

export const TEMPERA_AUDIENCES = Object.freeze(["palette", "tempo", "cradle", "remi", "human-data", "data-engine", "tempera-mcp", "tempera-code", "tempera-llm", "tempera-workflows", "tempera-gym"]);
export const DEFAULT_AUDIENCE = "palette";
export const TEMPERA_SCOPES = Object.freeze(["mcp:invoke", "memory:read", "memory:write", "memory:manage", "trace:read", "trace:write", "dataset:read", "dataset:write", "eval:run", "training:publish", "review:gold:manage", "review:resolve", "workflow:read", "workflow:write", "workflow:run", "model:read", "model:invoke", "pii:unmask", "admin"]);

export const TEMPERA_ISSUER_PATHS = Object.freeze({
  "authorize": "/oauth/authorize",
  "token": "/oauth/token",
  "revoke": "/oauth/revoke",
  "introspect": "/oauth/introspect",
  "mcp": "/mcp"
});

export const TEMPERA_ENVIRONMENTS = Object.freeze(
{
  "local": {
    "publicSiteUrl": "http://localhost:3000",
    "controlPlaneUrl": "http://localhost:8787",
    "authIssuerUrl": "http://localhost:8787",
    "authJwksUrl": "http://localhost:8787/.well-known/jwks.json",
    "mcpGatewayUrl": "http://localhost:8787/mcp",
    "dataEngineApiUrl": "http://127.0.0.1:8090",
    "temperaGymUrl": "http://127.0.0.1:8096",
    "cradleApiUrl": "http://127.0.0.1:8088",
    "temperaLlmApiUrl": "http://127.0.0.1:8080",
    "temperaWorkflowsApiUrl": "http://127.0.0.1:8095",
    "paletteApiUrl": "http://localhost:8080",
    "paletteMcpUrl": "http://localhost:8080/mcp",
    "tempoApiUrl": "http://localhost:7878"
  },
  "preview": {
    "publicSiteUrl": "https://tempera-public-site-git-preview-tempera.vercel.app",
    "controlPlaneUrl": "https://preview-api.tempera.dev",
    "authIssuerUrl": "https://preview-api.tempera.dev",
    "authJwksUrl": "https://preview-api.tempera.dev/.well-known/jwks.json",
    "mcpGatewayUrl": "https://preview-api.tempera.dev/mcp",
    "dataEngineApiUrl": "https://preview-data-engine.tempera.dev",
    "temperaGymUrl": "https://preview-gym.tempera.dev",
    "cradleApiUrl": "https://preview-cradle.tempera.dev",
    "temperaLlmApiUrl": "https://preview-llm.tempera.dev",
    "temperaWorkflowsApiUrl": "https://preview-workflows.tempera.dev",
    "paletteApiUrl": "https://preview-mcp.tempera.dev",
    "paletteMcpUrl": "https://preview-mcp.tempera.dev/mcp",
    "tempoApiUrl": "https://preview-tempo.tempera.dev"
  },
  "staging": {
    "publicSiteUrl": "https://staging.tempera.dev",
    "controlPlaneUrl": "https://staging-api.tempera.dev",
    "authIssuerUrl": "https://staging-api.tempera.dev",
    "authJwksUrl": "https://staging-api.tempera.dev/.well-known/jwks.json",
    "mcpGatewayUrl": "https://staging-api.tempera.dev/mcp",
    "dataEngineApiUrl": "https://staging-data-engine.tempera.dev",
    "temperaGymUrl": "https://staging-gym.tempera.dev",
    "cradleApiUrl": "https://staging-cradle.tempera.dev",
    "temperaLlmApiUrl": "https://staging-llm.tempera.dev",
    "temperaWorkflowsApiUrl": "https://staging-workflows.tempera.dev",
    "paletteApiUrl": "https://staging-mcp.tempera.dev",
    "paletteMcpUrl": "https://staging-mcp.tempera.dev/mcp",
    "tempoApiUrl": "https://staging-tempo.tempera.dev"
  },
  "production": {
    "publicSiteUrl": "https://tempera.dev",
    "controlPlaneUrl": "https://api.tempera.dev",
    "authIssuerUrl": "https://api.tempera.dev",
    "authJwksUrl": "https://api.tempera.dev/.well-known/jwks.json",
    "mcpGatewayUrl": "https://api.tempera.dev/mcp",
    "dataEngineApiUrl": "https://data-engine.tempera.dev",
    "temperaGymUrl": "https://gym.tempera.dev",
    "cradleApiUrl": "https://cradle.tempera.dev",
    "temperaLlmApiUrl": "https://llm.tempera.dev",
    "temperaWorkflowsApiUrl": "https://workflows.tempera.dev",
    "paletteApiUrl": "https://mcp.tempera.dev",
    "paletteMcpUrl": "https://mcp.tempera.dev/mcp",
    "tempoApiUrl": "https://tempo.tempera.dev"
  }
}
);

export const TEMPERA_PRODUCTS = Object.freeze(
{
  "controlPlane": {
    "name": "auth-hub",
    "repository": "https://github.com/tempera-dev/auth-hub",
    "envVar": "TEMPERA_CONTROL_PLANE_URL",
    "audience": null,
    "description": "Tempera control plane: unified accounts, OAuth issuance, workspaces, teams, API keys, billing, usage metering, and the unified MCP gateway."
  },
  "palette": {
    "name": "palette",
    "repository": "https://github.com/tempera-dev/palette",
    "envVar": "TEMPERA_PALETTE_URL",
    "audience": "palette",
    "description": "Agent observability: trace and span ingestion, search, datasets, evals, experiments, gates, and human review."
  },
  "tempo": {
    "name": "tempo",
    "repository": "https://github.com/tempera-dev/tempo",
    "envVar": "TEMPERA_TEMPO_URL",
    "audience": "tempo",
    "description": "Agent-native browser daemon (tempod): structured observation, batched actions, sessions, runs, and human handoff."
  },
  "temperaLlm": {
    "name": "tempera-llm",
    "repository": "https://github.com/tempera-dev/tempera-llm",
    "envVar": "TEMPERA_LLM_URL",
    "audience": "tempera-llm",
    "description": "OpenAI-compatible LLM gateway every Tempera product calls instead of hitting providers directly; reports LLM cost as model_cost usage events per the billing-credits contract."
  },
  "temperaWorkflows": {
    "name": "tempera-workflows",
    "repository": "https://github.com/tempera-dev/tempera-workflows",
    "envVar": "TEMPERA_WORKFLOWS_URL",
    "audience": "tempera-workflows",
    "description": "Deterministic workflow engine: bounded-DAG workflows (tempera.workflow/v1) of typed nodes executed as replayable, event-streamed runs; the run event stream (GET /v1/runs/{run_id}/events, SSE) is reachable through the raw passthrough request only."
  },
  "temperaGym": {
    "name": "tempera-gym",
    "repository": "https://github.com/tempera-dev/tempera-gym",
    "envVar": "TEMPERA_GYM_URL",
    "audience": "tempera-gym",
    "description": "RL environment pack service: environment catalog with implementation status, synchronous rollout execution, and persisted content-addressed trajectory-v1 runs."
  },
  "cradle": {
    "name": "cradle",
    "repository": "https://github.com/tempera-dev/cradle",
    "envVar": "TEMPERA_CRADLE_URL",
    "audience": "cradle",
    "description": "Capability sandbox daemon (cradled): synchronous and job-based sandboxed execution plus browser admission control."
  },
  "remi": {
    "name": "remi",
    "repository": "https://github.com/tempera-dev/remi",
    "envVar": "TEMPERA_REMI_URL",
    "audience": "remi",
    "description": "Temporal memory server: remember, project, query, and maintain an agent memory graph."
  },
  "dataEngine": {
    "name": "data-engine",
    "repository": "https://github.com/tempera-dev/data-engine",
    "envVar": "TEMPERA_DATA_ENGINE_URL",
    "audience": "data-engine",
    "description": "Domain-portable label-emergence engine: deterministic ingestion, sandboxed verification in cradle, and RL/eval/SFT dataset emission."
  },
  "humanData": {
    "name": "human-data",
    "repository": "https://github.com/tempera-dev/human-data",
    "envVar": "TEMPERA_HUMAN_DATA_URL",
    "audience": "human-data",
    "description": "Browser-agent human review: reviewers inspect provisioned browser-session evidence, record decisions, and return candidate cases to the agent quality loop. Passthrough client only; no typed operations yet."
  },
  "tempJs": {
    "name": "temp.js",
    "repository": "https://github.com/tempera-dev/temp.js",
    "envVar": "TEMPERA_TEMPJS_URL",
    "audience": null,
    "description": "Durable JavaScript runtime bridge for Tempera agents. Passthrough client only; no typed operations yet."
  },
  "tempOS": {
    "name": "tempOS",
    "repository": "https://github.com/tempera-dev/tempOS",
    "envVar": "TEMPERA_TEMPOS_URL",
    "audience": null,
    "description": "OS/runtime admission, policy, and receipt layer for agents. Passthrough client only; no typed operations yet."
  },
  "arrha": {
    "name": "Arrha",
    "repository": "https://github.com/tempera-dev/arrha",
    "envVar": "TEMPERA_ARRHA_URL",
    "audience": null,
    "description": "Settlement, chain, credits, and indexer layer for agent payments. Passthrough client only; no typed operations yet."
  }
}
);

export const TEMPERA_OPERATIONS = Object.freeze(
{
  "controlPlane": [
    {
      "id": "health",
      "upstreamOperationId": "getHealth",
      "method": "GET",
      "path": "/healthz",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check control-plane liveness; returns {ok: true}."
    },
    {
      "id": "getReadiness",
      "upstreamOperationId": "getReadiness",
      "method": "GET",
      "path": "/readyz",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Readiness probe for durable control-plane storage."
    },
    {
      "id": "me",
      "upstreamOperationId": "getMe",
      "method": "GET",
      "path": "/v1/me",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the authenticated user's identity, active workspace, and roles."
    },
    {
      "id": "listOrgs",
      "upstreamOperationId": "listOrganizations",
      "method": "GET",
      "path": "/v1/orgs",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List the organizations the authenticated user belongs to."
    },
    {
      "id": "createOrg",
      "upstreamOperationId": "createOrganization",
      "method": "POST",
      "path": "/v1/orgs",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "name"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "name"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Create an organization; the caller becomes its owner."
    },
    {
      "id": "listSessions",
      "upstreamOperationId": "listAccountSessions",
      "method": "GET",
      "path": "/v1/sessions",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List the user's active account sessions."
    },
    {
      "id": "createHostedSession",
      "upstreamOperationId": "createHostedSession",
      "method": "POST",
      "path": "/v1/sessions",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "mode",
        "email",
        "password",
        "organization",
        "inviteToken"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "email",
        "password"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Create a first-party hosted account session from email/password login or signup."
    },
    {
      "id": "revokeSession",
      "upstreamOperationId": "revokeAccountSession",
      "method": "DELETE",
      "path": "/v1/sessions/{id}",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Revoke an account session and its tokens immediately (idempotent)."
    },
    {
      "id": "selectWorkspace",
      "upstreamOperationId": "selectWorkspace",
      "method": "POST",
      "path": "/v1/workspace/select",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Switch the active workspace and receive a token pair scoped to it."
    },
    {
      "id": "listTeamMembers",
      "upstreamOperationId": "listTeamMembers",
      "method": "GET",
      "path": "/v1/team/members",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List team members of the active organization."
    },
    {
      "id": "updateTeamMember",
      "upstreamOperationId": "updateTeamMember",
      "method": "PATCH",
      "path": "/v1/team/members/{id}",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [
        "updateMask"
      ],
      "body": [
        "role"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "role"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Change a team member's role (requires an org admin role; at least one owner must remain)."
    },
    {
      "id": "removeTeamMember",
      "upstreamOperationId": "removeTeamMember",
      "method": "DELETE",
      "path": "/v1/team/members/{id}",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Remove a team member from the active organization (idempotent)."
    },
    {
      "id": "listInvites",
      "upstreamOperationId": "listInvites",
      "method": "GET",
      "path": "/v1/invites",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List invites for the active organization, newest first."
    },
    {
      "id": "createInvite",
      "upstreamOperationId": "createInvite",
      "method": "POST",
      "path": "/v1/invites",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "email",
        "role"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "email",
        "role"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Invite a user to the active organization; the accept URL is returned once."
    },
    {
      "id": "cancelInvite",
      "upstreamOperationId": "cancelInvite",
      "method": "DELETE",
      "path": "/v1/invites/{id}",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Cancel a pending invite (idempotent)."
    },
    {
      "id": "listProjects",
      "upstreamOperationId": "listProjects",
      "method": "GET",
      "path": "/v1/projects",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List projects across every organization the user belongs to."
    },
    {
      "id": "createProject",
      "upstreamOperationId": "createProject",
      "method": "POST",
      "path": "/v1/projects",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "name"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "name"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Create a project in an organization (requires an org admin role)."
    },
    {
      "id": "listEnvironments",
      "upstreamOperationId": "listEnvironments",
      "method": "GET",
      "path": "/v1/environments",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List environments across every project the user can access."
    },
    {
      "id": "createEnvironment",
      "upstreamOperationId": "createEnvironment",
      "method": "POST",
      "path": "/v1/environments",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "projectId",
        "name"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "projectId",
        "name"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Create an environment in a project (requires an org admin role)."
    },
    {
      "id": "listApiKeys",
      "upstreamOperationId": "listApiKeys",
      "method": "GET",
      "path": "/v1/api-keys",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List API keys in the active workspace; secrets are never returned."
    },
    {
      "id": "createApiKey",
      "upstreamOperationId": "createApiKey",
      "method": "POST",
      "path": "/v1/api-keys",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId",
        "name",
        "scopes",
        "audience",
        "expiresAt"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId",
        "scopes"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Mint a workspace API key (tp_...); the secret is returned exactly once. The workspace ids must match the token's workspace."
    },
    {
      "id": "revokeApiKey",
      "upstreamOperationId": "revokeApiKey",
      "method": "DELETE",
      "path": "/v1/api-keys/{id}",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Revoke an API key (idempotent)."
    },
    {
      "id": "rotateApiKey",
      "upstreamOperationId": "rotateApiKey",
      "method": "POST",
      "path": "/v1/api-keys/{id}/rotate",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Rotate an API key's secret; the new secret is returned exactly once."
    },
    {
      "id": "providerConnectionsList",
      "upstreamOperationId": "providerConnections.list",
      "method": "GET",
      "path": "/v1/provider-connections",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List provider connection metadata using a first-party account session. Secret references and values are never returned."
    },
    {
      "id": "providerConnectionsCreate",
      "upstreamOperationId": "providerConnections.create",
      "method": "POST",
      "path": "/v1/provider-connections",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId",
        "provider",
        "name",
        "secretRef",
        "allowedModels"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId",
        "provider",
        "name",
        "secretRef"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Create a tenant-scoped provider connection using only an external secret reference."
    },
    {
      "id": "providerConnectionsRevoke",
      "upstreamOperationId": "providerConnections.revoke",
      "method": "DELETE",
      "path": "/v1/provider-connections/{id}",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Revoke a provider connection immediately. Revoking an unknown id is a no-op."
    },
    {
      "id": "providerConnectionsRotate",
      "upstreamOperationId": "providerConnections.rotate",
      "method": "POST",
      "path": "/v1/provider-connections/{id}:rotate",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "secretRef",
        "allowedModels"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "secretRef"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Replace a connection secret reference and increment its revision without exposing the reference."
    },
    {
      "id": "providerConnectionsResolve",
      "upstreamOperationId": "providerConnections.resolve",
      "method": "POST",
      "path": "/v1/provider-connections/{id}:resolve",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId",
        "usageDelegation"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId",
        "usageDelegation"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Resolve connection runtime metadata for a tenant-bound tempera-llm service credential."
    },
    {
      "id": "experimentProviderConnectionsList",
      "upstreamOperationId": "experimentProviderConnections.list",
      "method": "GET",
      "path": "/v1/experiment-provider-connections",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List external experiment-provider metadata. Secret references and values are never returned."
    },
    {
      "id": "experimentProviderConnectionsCreate",
      "upstreamOperationId": "experimentProviderConnections.create",
      "method": "POST",
      "path": "/v1/experiment-provider-connections",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId",
        "provider",
        "providerKind",
        "name",
        "secretRef",
        "capabilities"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId",
        "provider",
        "providerKind",
        "name",
        "secretRef",
        "capabilities"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Register a tenant-scoped experiment provider using only an external secret reference."
    },
    {
      "id": "experimentProviderConnectionsRevoke",
      "upstreamOperationId": "experimentProviderConnections.revoke",
      "method": "DELETE",
      "path": "/v1/experiment-provider-connections/{id}",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Revoke an experiment-provider connection. An unknown id is a no-op."
    },
    {
      "id": "experimentProviderConnectionsResolve",
      "upstreamOperationId": "experimentProviderConnections.resolve",
      "method": "POST",
      "path": "/v1/experiment-provider-connections/{id}:resolve",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId",
        "approvalId",
        "proposalDigest",
        "protocolDigest",
        "mcpPrepareReceiptDigest",
        "mcpCommitReceiptDigest",
        "submissionIdempotencyKey"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId",
        "approvalId",
        "proposalDigest",
        "protocolDigest",
        "mcpPrepareReceiptDigest",
        "mcpCommitReceiptDigest",
        "submissionIdempotencyKey"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Atomically consume an exact human approval and resolve a provider reference for tempera-workflows."
    },
    {
      "id": "bioSignerKeysList",
      "upstreamOperationId": "bioSignerKeys.list",
      "method": "GET",
      "path": "/v1/bio-signer-keys",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List versioned public Ed25519 verifier keys for an authorized human administrator."
    },
    {
      "id": "bioSignerKeysCreate",
      "upstreamOperationId": "bioSignerKeys.create",
      "method": "POST",
      "path": "/v1/bio-signer-keys",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId",
        "keyId",
        "publicJwk"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId",
        "keyId",
        "publicJwk"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Register or rotate a public Ed25519 verifier key. Private key material is rejected."
    },
    {
      "id": "bioSignerKeysRevoke",
      "upstreamOperationId": "bioSignerKeys.revoke",
      "method": "DELETE",
      "path": "/v1/bio-signer-keys/{id}",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Revoke a public verifier key while retaining its history."
    },
    {
      "id": "experimentApprovalsList",
      "upstreamOperationId": "experimentApprovals.list",
      "method": "GET",
      "path": "/v1/experiment-approvals",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List exact, single-use experiment approvals for an authorized human approver."
    },
    {
      "id": "experimentApprovalsCreate",
      "upstreamOperationId": "experimentApprovals.create",
      "method": "POST",
      "path": "/v1/experiment-approvals",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId",
        "proposalDigest",
        "protocolDigest",
        "connectionId",
        "mcpPrepareReceiptDigest",
        "expiresAt"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId",
        "proposalDigest",
        "protocolDigest",
        "connectionId",
        "mcpPrepareReceiptDigest",
        "expiresAt"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Create a short-lived human approval bound to exact proposal, protocol, provider, and MCP preparation digests."
    },
    {
      "id": "experimentApprovalsRevoke",
      "upstreamOperationId": "experimentApprovals.revoke",
      "method": "DELETE",
      "path": "/v1/experiment-approvals/{id}",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Revoke an unused experiment approval. Consumed approvals remain immutable."
    },
    {
      "id": "listAuditLog",
      "upstreamOperationId": "listAuditLog",
      "method": "GET",
      "path": "/v1/audit-log",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List recent audit-log events for the user and active organization (up to 50, newest first)."
    },
    {
      "id": "listConnectors",
      "upstreamOperationId": "listConnectors",
      "method": "GET",
      "path": "/v1/connectors",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List the connector catalog (MCP clients, editors, and API surfaces)."
    },
    {
      "id": "getConnectorStatus",
      "upstreamOperationId": "getConnectorStatus",
      "method": "GET",
      "path": "/v1/connectors/{id}/status",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch one connector's connection status for the active workspace."
    },
    {
      "id": "listProducts",
      "upstreamOperationId": "listProducts",
      "method": "GET",
      "path": "/v1/products",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List the product catalog with default scopes and setup paths."
    },
    {
      "id": "getProductStatus",
      "upstreamOperationId": "getProductStatus",
      "method": "GET",
      "path": "/v1/products/{id}/status",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch one product's activation status, entitlements, signals, and usage meters."
    },
    {
      "id": "getBillingStatus",
      "upstreamOperationId": "getBillingStatus",
      "method": "GET",
      "path": "/v1/billing/status",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the organization's plan, subscription, usage meters, entitlements, invoices, and pricing (requires a billing role)."
    },
    {
      "id": "createBillingCheckout",
      "upstreamOperationId": "createBillingCheckout",
      "method": "GET",
      "path": "/v1/billing/checkout",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "rail",
        "plan",
        "planId",
        "interval",
        "currency",
        "network"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Create a checkout handoff URL for a plan on the chosen payment rail (requires a billing role)."
    },
    {
      "id": "getBillingPortal",
      "upstreamOperationId": "createBillingPortal",
      "method": "GET",
      "path": "/v1/billing/portal",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the billing-portal URL for the organization (requires a billing role)."
    },
    {
      "id": "getBillingCredits",
      "upstreamOperationId": "getBillingCredits",
      "method": "GET",
      "path": "/v1/billing/credits",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Return the org credit wallet balance, grant, overage, and recent ledger for owner, admin, or billing users. Internal cost/margin fields are redacted from the ledger for non-staff callers and returned in full only to platform staff."
    },
    {
      "id": "getModelCatalog",
      "upstreamOperationId": "getModelCatalog",
      "method": "GET",
      "path": "/v1/model-catalog",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "model:read",
      "description": "List the entitled Tempera Code model catalog; requires a tempera-code bearer with model:read and the model-gateway entitlement."
    },
    {
      "id": "recordUsage",
      "upstreamOperationId": "recordUsageEvent",
      "method": "POST",
      "path": "/v1/usage/events",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId",
        "metric",
        "quantity",
        "idempotencyKey",
        "cost"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId",
        "metric"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Record a usage event against a metered plan limit; requires a token carrying the meter's product scope and returns the updated meter."
    },
    {
      "id": "usageReservationsCreate",
      "upstreamOperationId": "usageReservations.create",
      "method": "POST",
      "path": "/v1/usage/reservations",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId",
        "subject",
        "idempotencyKey",
        "provider",
        "model",
        "configId",
        "byok",
        "maximumProviderCostMicros",
        "ttlSeconds"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId",
        "idempotencyKey",
        "provider",
        "model",
        "configId",
        "byok",
        "maximumProviderCostMicros"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Atomically reserve the maximum model cost before starting a provider request."
    },
    {
      "id": "usageReservationsCommit",
      "upstreamOperationId": "usageReservations.commit",
      "method": "POST",
      "path": "/v1/usage/reservations/{reservationId}:commit",
      "auth": "account",
      "pathParams": [
        "reservationId"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId",
        "configId",
        "cost"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId",
        "configId",
        "cost"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Commit exact provider usage against an admitted reservation and release unused capacity."
    },
    {
      "id": "usageReservationsRelease",
      "upstreamOperationId": "usageReservations.release",
      "method": "POST",
      "path": "/v1/usage/reservations/{reservationId}:release",
      "auth": "account",
      "pathParams": [
        "reservationId"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Release unused capacity after provider failure or cancellation."
    },
    {
      "id": "usageReservationsReconcile",
      "upstreamOperationId": "usageReservations.reconcile",
      "method": "POST",
      "path": "/v1/usage/reservations/{reservationId}:reconcile",
      "auth": "account",
      "pathParams": [
        "reservationId"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "projectId",
        "environmentId",
        "configId",
        "reason",
        "traceId",
        "observedUsage",
        "expectedCost"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "projectId",
        "environmentId",
        "configId",
        "reason",
        "observedUsage"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Hold maximum capacity and record non-secret evidence when exact provider usage is unavailable."
    },
    {
      "id": "listGrants",
      "upstreamOperationId": "listOAuthGrants",
      "method": "GET",
      "path": "/v1/oauth/grants",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List the OAuth grants the user has approved in the active workspace."
    },
    {
      "id": "revokeGrant",
      "upstreamOperationId": "revokeOAuthGrant",
      "method": "DELETE",
      "path": "/v1/oauth/grants/{id}",
      "auth": "account",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Revoke an OAuth grant and every refresh token issued under it."
    },
    {
      "id": "introspectToken",
      "upstreamOperationId": "introspectOAuthToken",
      "method": "POST",
      "path": "/v1/oauth/introspect",
      "auth": "introspectionSecret",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "token",
        "token_type_hint"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "token"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Introspect a token or tp_ API key server-side; requires the introspection secret and returns {active: false} for anything invalid."
    },
    {
      "id": "discovery",
      "upstreamOperationId": "getOAuthAuthorizationServerMetadata",
      "method": "GET",
      "path": "/.well-known/oauth-authorization-server",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch OAuth 2.1 authorization-server metadata for the issuer."
    },
    {
      "id": "getOAuthProtectedResourceMetadata",
      "upstreamOperationId": "getOAuthProtectedResourceMetadata",
      "method": "GET",
      "path": "/.well-known/oauth-protected-resource",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "OAuth protected resource discovery metadata for MCP/resource clients."
    },
    {
      "id": "protectedResourceMetadata",
      "upstreamOperationId": "getOAuthProtectedResourceMetadataForAudience",
      "method": "GET",
      "path": "/.well-known/oauth-protected-resource/{resource}",
      "auth": "none",
      "pathParams": [
        "resource"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch OAuth protected-resource metadata for one registered audience."
    },
    {
      "id": "jwks",
      "upstreamOperationId": "getJsonWebKeySet",
      "method": "GET",
      "path": "/.well-known/jwks.json",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the JSON Web Key Set used to verify control-plane access tokens."
    },
    {
      "id": "adminOperationalProvenance",
      "upstreamOperationId": "adminOperationalProvenance",
      "method": "GET",
      "path": "/v1/admin/operations/provenance",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Return fail-closed source, machine, and image provenance for the serving runtime to a platform-staff account session."
    },
    {
      "id": "adminStepUp",
      "upstreamOperationId": "adminStepUp",
      "method": "POST",
      "path": "/v1/admin/step-up",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "password"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "password"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Re-authenticate a platform-staff account session to mint a short-lived step-up elevation required for sensitive admin mutations."
    },
    {
      "id": "adminAdjustCredits",
      "upstreamOperationId": "adminAdjustCredits",
      "method": "POST",
      "path": "/v1/admin/billing/credits/adjust",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "orgId",
        "creditMicros",
        "reference",
        "reason"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "orgId",
        "creditMicros"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Platform-staff credit grant/adjustment to an org wallet. Requires a fresh step-up elevation; idempotent on the reference."
    },
    {
      "id": "adminBillingOrgs",
      "upstreamOperationId": "adminBillingOrgs",
      "method": "GET",
      "path": "/v1/admin/billing/orgs",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Platform-staff internal billing view: per-org wallet balances plus provider cost, customer charge, and margin economics."
    },
    {
      "id": "githubSetupSessionsCreate",
      "upstreamOperationId": "githubSetupSessions.create",
      "method": "POST",
      "path": "/v1/github/setup-sessions",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "projectId",
        "environmentId",
        "returnUrl"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Create a one-time CSRF-bound GitHub App installation session."
    },
    {
      "id": "githubSetupSessionsComplete",
      "upstreamOperationId": "githubSetupSessions.complete",
      "method": "GET",
      "path": "/github/callback",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "state",
        "installation_id"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Bind a GitHub installation callback to its authenticated workspace."
    },
    {
      "id": "githubInstallationsList",
      "upstreamOperationId": "githubInstallations.list",
      "method": "GET",
      "path": "/v1/github/installations",
      "auth": "account",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List active GitHub App installations for the organization."
    },
    {
      "id": "githubInstallationsDisconnect",
      "upstreamOperationId": "githubInstallations.disconnect",
      "method": "DELETE",
      "path": "/v1/github/installations/{installationId}",
      "auth": "account",
      "pathParams": [
        "installationId"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Disconnect a GitHub App installation from the workspace."
    },
    {
      "id": "githubInstallationRepositoriesList",
      "upstreamOperationId": "githubInstallationRepositories.list",
      "method": "GET",
      "path": "/v1/github/installations/{installationId}/repositories",
      "auth": "account",
      "pathParams": [
        "installationId"
      ],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List repository metadata received for a GitHub installation."
    },
    {
      "id": "githubRepositorySnapshotsCapture",
      "upstreamOperationId": "githubRepositorySnapshots.capture",
      "method": "POST",
      "path": "/v1/github/installations/{installationId}/repositories/{repositoryId}:snapshot",
      "auth": "account",
      "pathParams": [
        "installationId",
        "repositoryId"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "ref"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Capture an ephemeral, immutable GitHub repository snapshot for an authorized workspace."
    },
    {
      "id": "githubWebhooksAccept",
      "upstreamOperationId": "githubWebhooks.accept",
      "method": "POST",
      "path": "/github/webhook",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Accept a signed, replay-deduplicated GitHub webhook."
    }
  ],
  "palette": [
    {
      "id": "health",
      "upstreamOperationId": "health.check",
      "method": "GET",
      "path": "/health",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check palette API liveness; returns {ok: true}."
    },
    {
      "id": "alertsEvaluate",
      "upstreamOperationId": "alerts.evaluate",
      "method": "POST",
      "path": "/v1/alerts/{tenant_id}/{project_id}/traces/{trace_id}/webhook",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "trace_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "input",
        "policy"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "policy",
        "input"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/alerts/{tenant_id}/{project_id}/traces/{trace_id}/webhook."
    },
    {
      "id": "createApiKey",
      "upstreamOperationId": "apiKeys.create",
      "method": "POST",
      "path": "/v1/api-keys/{tenant_id}/{project_id}/{environment_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "environment_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "scopes"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "scopes"
      ],
      "bodyDefaults": {},
      "scope": "admin",
      "description": "Mint a palette-scoped API key; the secret is returned exactly once."
    },
    {
      "id": "revokeApiKey",
      "upstreamOperationId": "apiKeys.revoke",
      "method": "POST",
      "path": "/v1/api-keys/{tenant_id}/{project_id}/{environment_id}/{api_key_id}/revoke",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "environment_id",
        "api_key_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "admin",
      "description": "Revoke a palette API key."
    },
    {
      "id": "archiveQuerySpans",
      "upstreamOperationId": "archive.querySpans",
      "method": "GET",
      "path": "/v1/archive/{tenant_id}/{project_id}/spans",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "environment_id",
        "trace_id",
        "span_id",
        "kind",
        "status",
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/archive/{tenant_id}/{project_id}/spans."
    },
    {
      "id": "archiveTrace",
      "upstreamOperationId": "archive.archiveTrace",
      "method": "POST",
      "path": "/v1/archive/{tenant_id}/{project_id}/{trace_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "trace_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:read",
      "description": "Archive a trace to Parquet and return the archive manifest."
    },
    {
      "id": "auditList",
      "upstreamOperationId": "audit.list",
      "method": "GET",
      "path": "/v1/audit/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/audit/{tenant_id}/{project_id}."
    },
    {
      "id": "calibrationsRun",
      "upstreamOperationId": "calibrations.run",
      "method": "POST",
      "path": "/v1/calibrations/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "dataset_id",
        "version_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "eval_report_id",
        "evaluator_version_id",
        "pass_threshold"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/calibrations/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}."
    },
    {
      "id": "connectGetStatus",
      "upstreamOperationId": "connect.getStatus",
      "method": "GET",
      "path": "/v1/connect/status/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/connect/status/{tenant_id}/{project_id}."
    },
    {
      "id": "connectorsList",
      "upstreamOperationId": "connectors.list",
      "method": "GET",
      "path": "/v1/connectors/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/connectors/{tenant_id}/{project_id}."
    },
    {
      "id": "connectorsConnect",
      "upstreamOperationId": "connectors.connect",
      "method": "POST",
      "path": "/v1/connectors/{tenant_id}/{project_id}/connect",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "toolkit"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "toolkit"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/connectors/{tenant_id}/{project_id}/connect."
    },
    {
      "id": "connectorsInvokeTool",
      "upstreamOperationId": "connectors.invokeTool",
      "method": "POST",
      "path": "/v1/connectors/{tenant_id}/{project_id}/invoke",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "arguments",
        "tool"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "tool"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/connectors/{tenant_id}/{project_id}/invoke."
    },
    {
      "id": "connectorsGetSkills",
      "upstreamOperationId": "connectors.getSkills",
      "method": "GET",
      "path": "/v1/connectors/{tenant_id}/{project_id}/skills",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "toolkit"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/connectors/{tenant_id}/{project_id}/skills."
    },
    {
      "id": "connectorsStatus",
      "upstreamOperationId": "connectors.status",
      "method": "GET",
      "path": "/v1/connectors/{tenant_id}/{project_id}/status",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "toolkit"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/connectors/{tenant_id}/{project_id}/status."
    },
    {
      "id": "connectorsListTools",
      "upstreamOperationId": "connectors.listTools",
      "method": "GET",
      "path": "/v1/connectors/{tenant_id}/{project_id}/tools",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "toolkit",
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/connectors/{tenant_id}/{project_id}/tools."
    },
    {
      "id": "createDataset",
      "upstreamOperationId": "datasets.create",
      "method": "POST",
      "path": "/v1/datasets/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "name"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "name"
      ],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Create a dataset for curating cases from traces."
    },
    {
      "id": "promoteTraceToCase",
      "upstreamOperationId": "datasets.promoteCaseFromTrace",
      "method": "POST",
      "path": "/v1/datasets/{tenant_id}/{project_id}/{dataset_id}/cases/from-trace",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "dataset_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "reference",
        "span_id",
        "trace_id"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "trace_id"
      ],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Promote a trace (or one span of it) into a dataset case."
    },
    {
      "id": "createDatasetVersion",
      "upstreamOperationId": "datasets.createVersion",
      "method": "POST",
      "path": "/v1/datasets/{tenant_id}/{project_id}/{dataset_id}/versions",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "dataset_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "case_ids"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Snapshot a dataset into an immutable version for evals and experiments."
    },
    {
      "id": "evalsRunDeterministic",
      "upstreamOperationId": "evals.runDeterministic",
      "method": "POST",
      "path": "/v1/datasets/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/evals/deterministic",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "dataset_id",
        "version_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "agent_release_id",
        "code_hash",
        "evaluator_id",
        "evaluator_version_id",
        "kind",
        "prompt_version_id",
        "wasm_hash"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "evaluator_id",
        "evaluator_version_id",
        "agent_release_id",
        "kind"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/datasets/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/evals/deterministic."
    },
    {
      "id": "evalsRunJudge",
      "upstreamOperationId": "evals.runJudge",
      "method": "POST",
      "path": "/v1/datasets/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/evals/judge",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "dataset_id",
        "version_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "agent_release_id",
        "code_hash",
        "evaluator_id",
        "evaluator_version_id",
        "kind",
        "prompt_version_id",
        "provider_secret_id"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "evaluator_id",
        "evaluator_version_id",
        "agent_release_id",
        "kind",
        "provider_secret_id"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/datasets/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/evals/judge."
    },
    {
      "id": "importTemperaBundle",
      "upstreamOperationId": "evalResults.importTemperaBundle",
      "method": "POST",
      "path": "/v1/eval-results/{tenant_id}/{project_id}/tempera/bundles",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "canonical_json",
        "public_key_pem",
        "signature_base64"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "canonical_json",
        "signature_base64",
        "public_key_pem"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Import one RFC 8785-canonical, detached-Ed25519-signed official Tempera result bundle and return its minimal evidence receipt."
    },
    {
      "id": "recordTemperaDecision",
      "upstreamOperationId": "evalResults.recordTemperaDecision",
      "method": "POST",
      "path": "/v1/eval-results/{tenant_id}/{project_id}/tempera/decisions",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "canonical_json",
        "public_key_pem",
        "signature_base64"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "canonical_json",
        "signature_base64",
        "public_key_pem"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Import one RFC 8785-canonical, detached-Ed25519-signed preregistered Tempera A/B decision and return its minimal evidence receipt."
    },
    {
      "id": "getTemperaEvidence",
      "upstreamOperationId": "evalResults.getTemperaEvidence",
      "method": "GET",
      "path": "/v1/eval-results/{tenant_id}/{project_id}/tempera/{kind}/{external_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "kind",
        "external_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Fetch one tenant/project-scoped Tempera evidence receipt without returning its raw signed payload."
    },
    {
      "id": "experimentsRunDeterministic",
      "upstreamOperationId": "experiments.runDeterministic",
      "method": "POST",
      "path": "/v1/experiments/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/deterministic",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "dataset_id",
        "version_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "baseline_outputs",
        "baseline_release_id",
        "candidate_outputs",
        "candidate_release_id",
        "evaluator_id",
        "evaluator_version_id",
        "gate_policy",
        "kind"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "baseline_release_id",
        "candidate_release_id",
        "evaluator_id",
        "evaluator_version_id",
        "kind",
        "baseline_outputs",
        "candidate_outputs"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/experiments/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/deterministic."
    },
    {
      "id": "experimentsRunJudge",
      "upstreamOperationId": "experiments.runJudge",
      "method": "POST",
      "path": "/v1/experiments/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/judge",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "dataset_id",
        "version_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "baseline_outputs",
        "baseline_release_id",
        "candidate_outputs",
        "candidate_release_id",
        "evaluator_id",
        "evaluator_version_id",
        "gate_policy",
        "kind",
        "provider_secret_id"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "baseline_release_id",
        "candidate_release_id",
        "evaluator_id",
        "evaluator_version_id",
        "kind",
        "baseline_outputs",
        "candidate_outputs",
        "provider_secret_id"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/experiments/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/judge."
    },
    {
      "id": "gatesCreate",
      "upstreamOperationId": "gates.create",
      "method": "POST",
      "path": "/v1/gates/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "dataset_id",
        "evaluator_version_id",
        "gate_id",
        "inconclusive_policy",
        "name"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "gate_id",
        "name"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/gates/{tenant_id}/{project_id}."
    },
    {
      "id": "gatesRun",
      "upstreamOperationId": "gates.run",
      "method": "POST",
      "path": "/v1/gates/{tenant_id}/{project_id}/{gate_id}/run",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "gate_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "experiment_run_id"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/gates/{tenant_id}/{project_id}/{gate_id}/run."
    },
    {
      "id": "importSource",
      "upstreamOperationId": "ingest.importSource",
      "method": "POST",
      "path": "/v1/import/{tenant_id}/{project_id}/{environment_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "environment_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "durability"
      ],
      "body": [
        "payload",
        "source"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "source"
      ],
      "bodyDefaults": {},
      "scope": "trace:write",
      "description": "Import spans from a named external source payload."
    },
    {
      "id": "ingestReplayDeadLetter",
      "upstreamOperationId": "ingest.replayDeadLetter",
      "method": "POST",
      "path": "/v1/ingest/{tenant_id}/{project_id}/dead-letters/{message_id}/replay",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "message_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "reset_attempts"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/ingest/{tenant_id}/{project_id}/dead-letters/{message_id}/replay."
    },
    {
      "id": "ingestGetQueueStatus",
      "upstreamOperationId": "ingest.getQueueStatus",
      "method": "GET",
      "path": "/v1/ingest/{tenant_id}/{project_id}/queue",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/ingest/{tenant_id}/{project_id}/queue."
    },
    {
      "id": "ingestDrainTraceIngested",
      "upstreamOperationId": "ingest.drainTraceIngested",
      "method": "POST",
      "path": "/v1/ingest/{tenant_id}/{project_id}/trace-ingested/drain",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "limit"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/ingest/{tenant_id}/{project_id}/trace-ingested/drain."
    },
    {
      "id": "ingestDrainTraceWrites",
      "upstreamOperationId": "ingest.drainTraceWrites",
      "method": "POST",
      "path": "/v1/ingest/{tenant_id}/{project_id}/trace-writes/drain",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "limit"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/ingest/{tenant_id}/{project_id}/trace-writes/drain."
    },
    {
      "id": "ingestReconcileTrace",
      "upstreamOperationId": "ingest.reconcileTrace",
      "method": "POST",
      "path": "/v1/ingest/{tenant_id}/{project_id}/traces/{trace_id}/reconcile",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "trace_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/ingest/{tenant_id}/{project_id}/traces/{trace_id}/reconcile."
    },
    {
      "id": "judgeEvaluate",
      "upstreamOperationId": "judge.evaluate",
      "method": "POST",
      "path": "/v1/judge/{tenant_id}/{project_id}/evaluate",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "cache_namespace",
        "case",
        "evaluator",
        "provider_secret_id"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "evaluator",
        "case",
        "provider_secret_id"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/judge/{tenant_id}/{project_id}/evaluate."
    },
    {
      "id": "judgeListLedger",
      "upstreamOperationId": "judge.listLedger",
      "method": "GET",
      "path": "/v1/judge/{tenant_id}/{project_id}/ledger",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/judge/{tenant_id}/{project_id}/ledger."
    },
    {
      "id": "onlineDecideSampling",
      "upstreamOperationId": "online.decideSampling",
      "method": "POST",
      "path": "/v1/online/{tenant_id}/{project_id}/traces/{trace_id}/sampling",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "trace_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "high_cost_micros_threshold",
        "keep_errors",
        "sample_rate_per_mille",
        "slow_ms_threshold"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "sample_rate_per_mille",
        "keep_errors"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/online/{tenant_id}/{project_id}/traces/{trace_id}/sampling."
    },
    {
      "id": "promptsList",
      "upstreamOperationId": "prompts.list",
      "method": "GET",
      "path": "/v1/prompts/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/prompts/{tenant_id}/{project_id}."
    },
    {
      "id": "promptsCreate",
      "upstreamOperationId": "prompts.create",
      "method": "POST",
      "path": "/v1/prompts/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "created_by",
        "description",
        "message",
        "name",
        "template"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "name",
        "template"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/prompts/{tenant_id}/{project_id}."
    },
    {
      "id": "promptsGet",
      "upstreamOperationId": "prompts.get",
      "method": "GET",
      "path": "/v1/prompts/{tenant_id}/{project_id}/{prompt_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "prompt_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/prompts/{tenant_id}/{project_id}/{prompt_id}."
    },
    {
      "id": "promptsDiffVersions",
      "upstreamOperationId": "prompts.diffVersions",
      "method": "GET",
      "path": "/v1/prompts/{tenant_id}/{project_id}/{prompt_id}/diff",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "prompt_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "from",
        "to"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/prompts/{tenant_id}/{project_id}/{prompt_id}/diff."
    },
    {
      "id": "promptsListVersions",
      "upstreamOperationId": "prompts.listVersions",
      "method": "GET",
      "path": "/v1/prompts/{tenant_id}/{project_id}/{prompt_id}/versions",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "prompt_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/prompts/{tenant_id}/{project_id}/{prompt_id}/versions."
    },
    {
      "id": "promptsAddVersion",
      "upstreamOperationId": "prompts.addVersion",
      "method": "POST",
      "path": "/v1/prompts/{tenant_id}/{project_id}/{prompt_id}/versions",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "prompt_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "created_by",
        "message",
        "template"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "template"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/prompts/{tenant_id}/{project_id}/{prompt_id}/versions."
    },
    {
      "id": "providerSecretsList",
      "upstreamOperationId": "providerSecrets.list",
      "method": "GET",
      "path": "/v1/provider-secrets/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/provider-secrets/{tenant_id}/{project_id}."
    },
    {
      "id": "providerSecretsCreate",
      "upstreamOperationId": "providerSecrets.create",
      "method": "POST",
      "path": "/v1/provider-secrets/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "display_name",
        "provider",
        "secret_value"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "provider",
        "display_name",
        "secret_value"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/provider-secrets/{tenant_id}/{project_id}."
    },
    {
      "id": "providerSecretsRevoke",
      "upstreamOperationId": "providerSecrets.revoke",
      "method": "POST",
      "path": "/v1/provider-secrets/{tenant_id}/{project_id}/{provider_secret_id}/revoke",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "provider_secret_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/provider-secrets/{tenant_id}/{project_id}/{provider_secret_id}/revoke."
    },
    {
      "id": "reviewsCreateQueue",
      "upstreamOperationId": "reviews.createQueue",
      "method": "POST",
      "path": "/v1/review-queues/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "annotation_schema",
        "name",
        "queue_id"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "name",
        "annotation_schema"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/review-queues/{tenant_id}/{project_id}."
    },
    {
      "id": "reviewsListTasks",
      "upstreamOperationId": "reviews.listTasks",
      "method": "GET",
      "path": "/v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "queue_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "state",
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks."
    },
    {
      "id": "reviewsEnqueueTaskFromTrace",
      "upstreamOperationId": "reviews.enqueueTaskFromTrace",
      "method": "POST",
      "path": "/v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks/from-trace",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "queue_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "dataset_case_id",
        "dataset_id",
        "priority",
        "span_id",
        "task_id",
        "trace_id"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "trace_id"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks/from-trace."
    },
    {
      "id": "reviewsSubmitAnnotation",
      "upstreamOperationId": "reviews.submitAnnotation",
      "method": "POST",
      "path": "/v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks/{task_id}/annotations",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "queue_id",
        "task_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "annotation_id",
        "payload",
        "reviewer_id",
        "verdict"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "reviewer_id",
        "verdict",
        "payload"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks/{task_id}/annotations."
    },
    {
      "id": "reviewsPromoteAnnotation",
      "upstreamOperationId": "reviews.promoteAnnotation",
      "method": "POST",
      "path": "/v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks/{task_id}/annotations/{annotation_id}/promote",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "queue_id",
        "task_id",
        "annotation_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "dataset_id",
        "reference"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "dataset_id"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks/{task_id}/annotations/{annotation_id}/promote."
    },
    {
      "id": "scenariosList",
      "upstreamOperationId": "scenarios.list",
      "method": "GET",
      "path": "/v1/scenarios/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/scenarios/{tenant_id}/{project_id}."
    },
    {
      "id": "scenariosCreate",
      "upstreamOperationId": "scenarios.create",
      "method": "POST",
      "path": "/v1/scenarios/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "exemplar_trace_id",
        "expected_outcome",
        "failure_mode",
        "source_trace_ids",
        "title"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "title",
        "source_trace_ids"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/scenarios/{tenant_id}/{project_id}."
    },
    {
      "id": "scenariosMine",
      "upstreamOperationId": "scenarios.mine",
      "method": "POST",
      "path": "/v1/scenarios/{tenant_id}/{project_id}/mine",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "jaccard_threshold",
        "trace_ids"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "trace_ids"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/scenarios/{tenant_id}/{project_id}/mine."
    },
    {
      "id": "scenariosGet",
      "upstreamOperationId": "scenarios.get",
      "method": "GET",
      "path": "/v1/scenarios/{tenant_id}/{project_id}/{scenario_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "scenario_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/scenarios/{tenant_id}/{project_id}/{scenario_id}."
    },
    {
      "id": "searchSpans",
      "upstreamOperationId": "search.spans",
      "method": "GET",
      "path": "/v1/search/{tenant_id}/spans",
      "auth": "product",
      "pathParams": [
        "tenant_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "q",
        "project_id",
        "environment_id",
        "trace_id",
        "span_id",
        "kind",
        "status",
        "model",
        "tool",
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:read",
      "description": "Search spans by text query and facet filters."
    },
    {
      "id": "getSpan",
      "upstreamOperationId": "spans.get",
      "method": "GET",
      "path": "/v1/spans/{tenant_id}/{trace_id}/{span_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "trace_id",
        "span_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "unmask",
        "reason"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:read",
      "description": "Fetch one canonical span by trace and span id."
    },
    {
      "id": "getSpanIo",
      "upstreamOperationId": "spans.getIo",
      "method": "GET",
      "path": "/v1/spans/{tenant_id}/{trace_id}/{span_id}/io",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "trace_id",
        "span_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "unmask",
        "reason"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:read",
      "description": "Fetch a span's recorded input and output values."
    },
    {
      "id": "ingestSpan",
      "upstreamOperationId": "ingest.native",
      "method": "POST",
      "path": "/v1/traces/native",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "durability"
      ],
      "body": [
        "attributes",
        "auth_context",
        "cost",
        "end_time",
        "idempotency_key",
        "input",
        "kind",
        "model",
        "name",
        "output",
        "parent_span_id",
        "redaction_class",
        "scope",
        "seq",
        "span_id",
        "start_time",
        "status",
        "tokens",
        "trace_id"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "scope",
        "trace_id",
        "span_id",
        "seq",
        "kind",
        "name",
        "status",
        "attributes",
        "redaction_class"
      ],
      "bodyDefaults": {},
      "scope": "trace:write",
      "description": "Ingest one native span; idempotent when an idempotency key is supplied."
    },
    {
      "id": "listTraces",
      "upstreamOperationId": "traces.list",
      "method": "GET",
      "path": "/v1/traces/{tenant_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "project_id",
        "environment_id",
        "trace_id",
        "kind",
        "status",
        "started_after",
        "started_before",
        "model",
        "release",
        "min_cost_micros",
        "max_cost_micros",
        "min_latency_ms",
        "max_latency_ms",
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:read",
      "description": "List trace summaries for a tenant with filters and cursor pagination."
    },
    {
      "id": "getTrace",
      "upstreamOperationId": "traces.get",
      "method": "GET",
      "path": "/v1/traces/{tenant_id}/{trace_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "trace_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "unmask",
        "reason"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:read",
      "description": "Fetch one full trace with all canonical spans; unmasking PII requires the pii:unmask scope and a reason."
    },
    {
      "id": "getUsageSummary",
      "upstreamOperationId": "usage.getSummary",
      "method": "GET",
      "path": "/v1/usage/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "admin",
      "description": "Fetch usage totals for a tenant project."
    }
  ],
  "tempo": [
    {
      "id": "agentCard",
      "upstreamOperationId": "agentCard",
      "method": "GET",
      "path": "/.well-known/agent-card.json",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /.well-known/agent-card.json."
    },
    {
      "id": "agentJson",
      "upstreamOperationId": "agentJson",
      "method": "GET",
      "path": "/.well-known/agent.json",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /.well-known/agent.json."
    },
    {
      "id": "drain",
      "upstreamOperationId": "drain",
      "method": "POST",
      "path": "/drain",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /drain."
    },
    {
      "id": "health",
      "upstreamOperationId": "health",
      "method": "GET",
      "path": "/health",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check tempod liveness; returns {ok: true}."
    },
    {
      "id": "metrics",
      "upstreamOperationId": "metrics",
      "method": "GET",
      "path": "/metrics",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /metrics."
    },
    {
      "id": "openapi",
      "upstreamOperationId": "openapi",
      "method": "GET",
      "path": "/openapi.json",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch tempod's OpenAPI document, generated at runtime for this host."
    },
    {
      "id": "ready",
      "upstreamOperationId": "ready",
      "method": "GET",
      "path": "/ready",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check tempod readiness, including engine attachment, drain state, and session capacity."
    },
    {
      "id": "listRuns",
      "upstreamOperationId": "listRuns",
      "method": "GET",
      "path": "/runs",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "session_id"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List agent runs, optionally filtered to one session."
    },
    {
      "id": "getRun",
      "upstreamOperationId": "getRun",
      "method": "GET",
      "path": "/runs/{run_id}",
      "auth": "product",
      "pathParams": [
        "run_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch one agent run with its state."
    },
    {
      "id": "cancelRun",
      "upstreamOperationId": "cancelRun",
      "method": "POST",
      "path": "/runs/{run_id}/cancel",
      "auth": "product",
      "pathParams": [
        "run_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Cancel an agent run."
    },
    {
      "id": "runEvents",
      "upstreamOperationId": "runEvents",
      "method": "GET",
      "path": "/runs/{run_id}/events",
      "auth": "product",
      "pathParams": [
        "run_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "after_seq"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /runs/{run_id}/events."
    },
    {
      "id": "resumeRun",
      "upstreamOperationId": "resumeRun",
      "method": "POST",
      "path": "/runs/{run_id}/resume",
      "auth": "product",
      "pathParams": [
        "run_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Resume an agent run after a human handoff completes."
    },
    {
      "id": "listSessions",
      "upstreamOperationId": "listSessions",
      "method": "GET",
      "path": "/sessions",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List browser sessions with their state and creation time."
    },
    {
      "id": "createSession",
      "upstreamOperationId": "createSession",
      "method": "POST",
      "path": "/sessions",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "driverless",
        "url"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "url"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Open a browser session at a URL; driverless sessions skip engine attachment."
    },
    {
      "id": "closeSession",
      "upstreamOperationId": "closeSession",
      "method": "DELETE",
      "path": "/sessions/{session_id}",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Close a browser session and release its engine resources."
    },
    {
      "id": "actBatch",
      "upstreamOperationId": "actBatchSession",
      "method": "POST",
      "path": "/sessions/{session_id}/act_batch",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "batch",
        "confirmation_grant",
        "confirmed",
        "idempotency_key",
        "input_tainted",
        "payment_context"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "batch"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Apply a batch of semantic actions with policy gating; returns the applied diff or a policy decision."
    },
    {
      "id": "adoptSession",
      "upstreamOperationId": "adoptSession",
      "method": "POST",
      "path": "/sessions/{session_id}/adopt",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "engine_tier",
        "label",
        "platform",
        "profile_id",
        "storage_continuity",
        "surface_id"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Let a human surface take write ownership of the session and receive an adoption lease."
    },
    {
      "id": "grantConfirmation",
      "upstreamOperationId": "grantSessionConfirmation",
      "method": "POST",
      "path": "/sessions/{session_id}/confirmations/{confirmation_id}",
      "auth": "product",
      "pathParams": [
        "session_id",
        "confirmation_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Grant a pending policy confirmation and receive a single-use grant token."
    },
    {
      "id": "sessionEvents",
      "upstreamOperationId": "sessionEvents",
      "method": "GET",
      "path": "/sessions/{session_id}/events",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "after_seq"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the session's event window after a sequence number."
    },
    {
      "id": "handoffSession",
      "upstreamOperationId": "handoffSession",
      "method": "POST",
      "path": "/sessions/{session_id}/handoff",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Return write ownership of the session to the agent plane."
    },
    {
      "id": "managerSession",
      "upstreamOperationId": "managerSession",
      "method": "GET",
      "path": "/sessions/{session_id}/manager",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /sessions/{session_id}/manager."
    },
    {
      "id": "observe",
      "upstreamOperationId": "observeSession",
      "method": "GET",
      "path": "/sessions/{session_id}/observe",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the session's compiled structured observation (ranked, stably-identified elements)."
    },
    {
      "id": "createRun",
      "upstreamOperationId": "createSessionRun",
      "method": "POST",
      "path": "/sessions/{session_id}/runs",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "actions",
        "goal",
        "max_rounds",
        "token_budget"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Start an agent run against the session with a goal, action budget, and round limit."
    },
    {
      "id": "screenshot",
      "upstreamOperationId": "screenshotSession",
      "method": "GET",
      "path": "/sessions/{session_id}/screenshot",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "pathParamTemplates": {},
      "query": [
        "set_of_marks"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Capture a PNG screenshot of the session, optionally annotated with set-of-marks."
    },
    {
      "id": "registerSessionSurface",
      "upstreamOperationId": "registerSessionSurface",
      "method": "POST",
      "path": "/sessions/{session_id}/surfaces",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "engine_tier",
        "label",
        "platform",
        "profile_id",
        "storage_continuity",
        "surface_id"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /sessions/{session_id}/surfaces."
    },
    {
      "id": "removeSessionSurface",
      "upstreamOperationId": "removeSessionSurface",
      "method": "DELETE",
      "path": "/sessions/{session_id}/surfaces/{surface_id}",
      "auth": "product",
      "pathParams": [
        "session_id",
        "surface_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call DELETE /sessions/{session_id}/surfaces/{surface_id}."
    },
    {
      "id": "transformSession",
      "upstreamOperationId": "transformSession",
      "method": "POST",
      "path": "/sessions/{session_id}/transform",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "determinism",
        "idempotency_key",
        "input",
        "lane",
        "source",
        "spans"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "lane",
        "source"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /sessions/{session_id}/transform."
    }
  ],
  "temperaLlm": [
    {
      "id": "health",
      "upstreamOperationId": "health.check",
      "method": "GET",
      "path": "/healthz",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check tempera-llm gateway liveness; returns {ok: true}."
    },
    {
      "id": "readinessCheck",
      "upstreamOperationId": "readiness.check",
      "method": "GET",
      "path": "/readyz",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /readyz."
    },
    {
      "id": "createChatCompletion",
      "upstreamOperationId": "chatCompletions.create",
      "method": "POST",
      "path": "/v1/chat/completions",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "byok",
        "max_tokens",
        "messages",
        "model",
        "response_format",
        "stream",
        "temperature"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "model",
        "messages",
        "max_tokens"
      ],
      "bodyDefaults": {},
      "scope": "model:invoke",
      "description": "Create a non-streaming OpenAI-compatible chat completion through the tempera-llm gateway."
    },
    {
      "id": "listModels",
      "upstreamOperationId": "models.list",
      "method": "GET",
      "path": "/v1/models",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "model:read",
      "description": "List the configured model catalog the gateway can route to."
    },
    {
      "id": "createResponse",
      "upstreamOperationId": "responses.create",
      "method": "POST",
      "path": "/v1/responses",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "byok",
        "input",
        "max_output_tokens",
        "model",
        "response_format"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "model",
        "input",
        "max_output_tokens"
      ],
      "bodyDefaults": {},
      "scope": "model:invoke",
      "description": "Create a non-streaming OpenAI Responses-style inference request through the tempera-llm gateway."
    }
  ],
  "temperaWorkflows": [
    {
      "id": "health",
      "upstreamOperationId": "healthz",
      "method": "GET",
      "path": "/healthz",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check tempera-workflows engine liveness."
    },
    {
      "id": "listNodeTypes",
      "upstreamOperationId": "nodeTypes.list",
      "method": "GET",
      "path": "/v1/node-types",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:read",
      "description": "List the typed node catalog: native orchestration nodes plus the sdk.<product>.<operation> nodes generated from the SDK surface."
    },
    {
      "id": "listRuns",
      "upstreamOperationId": "runs.list",
      "method": "GET",
      "path": "/v1/runs",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "workflowId",
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:read",
      "description": "List workflow runs, optionally filtered to one workflow."
    },
    {
      "id": "getRun",
      "upstreamOperationId": "runs.get",
      "method": "GET",
      "path": "/v1/runs/{runId}",
      "auth": "product",
      "pathParams": [
        "runId"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:read",
      "description": "Fetch one workflow run with its state, node results, and timings; the live SSE event stream at /v1/runs/{run_id}/events is passthrough-only."
    },
    {
      "id": "cancelRun",
      "upstreamOperationId": "runs.cancel",
      "method": "POST",
      "path": "/v1/runs/{runId}:cancel",
      "auth": "product",
      "pathParams": [
        "runId"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:run",
      "description": "Cancel a queued or running workflow run."
    },
    {
      "id": "listWorkflows",
      "upstreamOperationId": "workflows.list",
      "method": "GET",
      "path": "/v1/workflows",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:read",
      "description": "List stored workflow definitions, newest first."
    },
    {
      "id": "createWorkflow",
      "upstreamOperationId": "workflows.create",
      "method": "POST",
      "path": "/v1/workflows",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "contractVersion",
        "description",
        "edges",
        "id",
        "name",
        "nodes",
        "settings"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "contractVersion",
        "id",
        "name",
        "nodes",
        "edges"
      ],
      "bodyDefaults": {},
      "scope": "workflow:write",
      "description": "Create a workflow definition (tempera.workflow/v1 bounded DAG of typed nodes); the definition is validated before it is stored."
    },
    {
      "id": "getWorkflow",
      "upstreamOperationId": "workflows.get",
      "method": "GET",
      "path": "/v1/workflows/{workflowId}",
      "auth": "product",
      "pathParams": [
        "workflowId"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:read",
      "description": "Fetch one stored workflow definition."
    },
    {
      "id": "deleteWorkflow",
      "upstreamOperationId": "workflows.delete",
      "method": "DELETE",
      "path": "/v1/workflows/{workflowId}",
      "auth": "product",
      "pathParams": [
        "workflowId"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:write",
      "description": "Delete a stored workflow definition."
    },
    {
      "id": "updateWorkflow",
      "upstreamOperationId": "workflows.update",
      "method": "PATCH",
      "path": "/v1/workflows/{workflowId}",
      "auth": "product",
      "pathParams": [
        "workflowId"
      ],
      "pathParamTemplates": {},
      "query": [
        "updateMask"
      ],
      "body": [
        "contractVersion",
        "description",
        "edges",
        "id",
        "name",
        "nodes",
        "settings"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "contractVersion",
        "id",
        "name",
        "nodes",
        "edges"
      ],
      "bodyDefaults": {},
      "scope": "workflow:write",
      "description": "Replace a stored workflow definition with a new validated revision."
    },
    {
      "id": "createRun",
      "upstreamOperationId": "runs.create",
      "method": "POST",
      "path": "/v1/workflows/{workflowId}/runs",
      "auth": "product",
      "pathParams": [
        "workflowId"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "idempotencyKey",
        "input",
        "only",
        "seedOutputs",
        "startAt",
        "usePinned"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:run",
      "description": "Start a run of a stored workflow with an optional input document and idempotency key."
    },
    {
      "id": "callWorkflow",
      "upstreamOperationId": "workflows.call",
      "method": "POST",
      "path": "/v1/workflows/{workflowId}:call",
      "auth": "product",
      "pathParams": [
        "workflowId"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "idempotencyKey",
        "input",
        "only",
        "seedOutputs",
        "startAt",
        "usePinned",
        "waitMs"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:run",
      "description": "Run a workflow to completion and return its output in a single call."
    },
    {
      "id": "composeWorkflow",
      "upstreamOperationId": "workflows.compose",
      "method": "POST",
      "path": "/v1/workflows/{workflowId}:compose",
      "auth": "product",
      "pathParams": [
        "workflowId"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "attachments",
        "draft",
        "history",
        "model",
        "prompt"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "prompt"
      ],
      "bodyDefaults": {},
      "scope": "workflow:write",
      "description": "Search the full SDK-backed node catalog or ask Tempera Code to propose a validated workflow draft without saving or running it."
    },
    {
      "id": "assistJson",
      "upstreamOperationId": "workflows.assistJson",
      "method": "POST",
      "path": "/v1/workflows:assistJson",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "context",
        "current",
        "expectedRoot",
        "mode",
        "prompt",
        "purpose"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "mode",
        "purpose",
        "expectedRoot"
      ],
      "bodyDefaults": {},
      "scope": "workflow:write",
      "description": "Generate or repair one JSON editor value and validate its requested root and purpose without saving a workflow or executing a node."
    },
    {
      "id": "validateWorkflow",
      "upstreamOperationId": "workflows.validate",
      "method": "POST",
      "path": "/v1/workflows:validate",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "contractVersion",
        "description",
        "edges",
        "id",
        "name",
        "nodes",
        "settings"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "contractVersion",
        "id",
        "name",
        "nodes",
        "edges"
      ],
      "bodyDefaults": {},
      "scope": "workflow:write",
      "description": "Validate a workflow definition without storing it; returns the full diagnostic list."
    }
  ],
  "temperaGym": [
    {
      "id": "health",
      "upstreamOperationId": "health.get",
      "method": "GET",
      "path": "/healthz",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check tempera-gym service liveness."
    },
    {
      "id": "listEnvironments",
      "upstreamOperationId": "environments.list",
      "method": "GET",
      "path": "/v1/environments",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List the gym pack's environment catalog, including implementation status and per-environment manifests."
    },
    {
      "id": "listRuns",
      "upstreamOperationId": "runs.list",
      "method": "GET",
      "path": "/v1/runs",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "environmentId",
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List persisted rollout run index records, newest first."
    },
    {
      "id": "getRun",
      "upstreamOperationId": "runs.get",
      "method": "GET",
      "path": "/v1/runs/{run}",
      "auth": "product",
      "pathParams": [
        "run"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one persisted run's index record and verified trajectory-v1 envelope by run id or trajectory content hash."
    },
    {
      "id": "createRollout",
      "upstreamOperationId": "rollouts.create",
      "method": "POST",
      "path": "/v1/rollouts",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "environmentId",
        "policy",
        "seed",
        "maxSteps",
        "model",
        "dataEngineProductId",
        "dataEngineMaxRecords"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "environmentId",
        "seed"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Execute one rollout synchronously, persist the trajectory, and return the completed operation envelope."
    }
  ],
  "cradle": [
    {
      "id": "projectsBrowserAdaptersIssueCapability",
      "upstreamOperationId": "projects.browserAdapters.issueCapability",
      "method": "POST",
      "path": "/v1/browser/adapter/capability",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "actor",
        "adapter_id",
        "sensitive_activity_mode",
        "sensitivity",
        "ttl_seconds"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "actor",
        "sensitivity"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/browser/adapter/capability."
    },
    {
      "id": "projectsBrowserAdaptersValidateCompletion",
      "upstreamOperationId": "projects.browserAdapters.validateCompletion",
      "method": "POST",
      "path": "/v1/browser/adapter/completion/validate",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "adapter_id",
        "contract_version",
        "egress_log_sealed_or_discarded",
        "notes",
        "plaintext_artifacts_removed",
        "process_terminated",
        "proof_ids",
        "request_id",
        "sealed_artifact_handles",
        "temporary_profile_removed"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "request_id",
        "adapter_id",
        "contract_version",
        "process_terminated",
        "temporary_profile_removed",
        "plaintext_artifacts_removed",
        "egress_log_sealed_or_discarded",
        "sealed_artifact_handles",
        "proof_ids",
        "notes"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/browser/adapter/completion/validate."
    },
    {
      "id": "getBrowserAdapterContract",
      "upstreamOperationId": "projects.browserAdapters.getContract",
      "method": "GET",
      "path": "/v1/browser/adapter/contract",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the browser adapter contract, required controls, and conformance profile."
    },
    {
      "id": "projectsBrowserAdaptersClaimLaunch",
      "upstreamOperationId": "projects.browserAdapters.claimLaunch",
      "method": "POST",
      "path": "/v1/browser/adapter/launch/claim",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "launch_request"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "launch_request"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/browser/adapter/launch/claim."
    },
    {
      "id": "projectsBrowserAdaptersPlanLaunch",
      "upstreamOperationId": "projects.browserAdapters.planLaunch",
      "method": "POST",
      "path": "/v1/browser/adapter/launch/plan",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "admission",
        "manifest",
        "same_user_capability"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "same_user_capability",
        "admission",
        "manifest"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/browser/adapter/launch/plan."
    },
    {
      "id": "projectsBrowserAdaptersRegister",
      "upstreamOperationId": "projects.browserAdapters.register",
      "method": "POST",
      "path": "/v1/browser/adapter/register",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "actor",
        "manifest",
        "same_user_capability",
        "sensitivity"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "actor",
        "sensitivity",
        "same_user_capability",
        "manifest"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/browser/adapter/register."
    },
    {
      "id": "projectsBrowserAdaptersValidate",
      "upstreamOperationId": "projects.browserAdapters.validate",
      "method": "POST",
      "path": "/v1/browser/adapter/validate",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "adapter_id",
        "completion_proofs",
        "contract_version",
        "guard_fields",
        "launch_endpoint",
        "supported_controls",
        "supported_levels"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "adapter_id",
        "contract_version",
        "launch_endpoint",
        "supported_levels",
        "supported_controls",
        "guard_fields",
        "completion_proofs"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/browser/adapter/validate."
    },
    {
      "id": "admitBrowserSession",
      "upstreamOperationId": "projects.browserSessions.admit",
      "method": "POST",
      "path": "/v1/browser/admit",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "actor",
        "allow_downgrade",
        "artifact_mode",
        "credential_mode",
        "requested_level",
        "required_controls",
        "sensitive_activity_mode",
        "sensitivity",
        "target_origins",
        "task_label"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "requested_level",
        "actor",
        "sensitivity"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Request admission for a browser session at a sandbox level and receive the guard plan."
    },
    {
      "id": "getBrowserProfiles",
      "upstreamOperationId": "projects.browserProfiles.get",
      "method": "GET",
      "path": "/v1/browser/profiles",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the browser sandbox profile levels and suppression modes this daemon offers."
    },
    {
      "id": "getCapabilities",
      "upstreamOperationId": "projects.capabilities.get",
      "method": "GET",
      "path": "/v1/capabilities",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the sandbox capability matrix: lanes, engines, limits, and integrations."
    },
    {
      "id": "execute",
      "upstreamOperationId": "projects.executions.execute",
      "method": "POST",
      "path": "/v1/execute",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "entrypoint",
        "idempotency_key",
        "input",
        "lane",
        "policy",
        "source",
        "stdin"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "lane",
        "source"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Execute source synchronously in a sandbox lane and return the result with metrics."
    },
    {
      "id": "health",
      "upstreamOperationId": "health",
      "method": "GET",
      "path": "/v1/health",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check sandbox-daemon liveness; returns status, version, and uptime."
    },
    {
      "id": "getIntegrationContract",
      "upstreamOperationId": "projects.integration.get",
      "method": "GET",
      "path": "/v1/integration",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the ecosystem integration contract this daemon implements."
    },
    {
      "id": "createJob",
      "upstreamOperationId": "projects.jobs.create",
      "method": "POST",
      "path": "/v1/jobs",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "entrypoint",
        "idempotency_key",
        "input",
        "lane",
        "policy",
        "source",
        "stdin"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "lane",
        "source"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Submit an asynchronous sandbox job; returns an operation handle to poll."
    },
    {
      "id": "getJob",
      "upstreamOperationId": "projects.jobs.get",
      "method": "GET",
      "path": "/v1/jobs/{id}",
      "auth": "product",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch a sandbox job's status and result."
    },
    {
      "id": "cancelJob",
      "upstreamOperationId": "projects.jobs.cancel",
      "method": "DELETE",
      "path": "/v1/jobs/{id}",
      "auth": "product",
      "pathParams": [
        "id"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Cancel a queued or running sandbox job (idempotent for already-cancelled jobs)."
    },
    {
      "id": "projectsModulesCreate",
      "upstreamOperationId": "projects.modules.create",
      "method": "POST",
      "path": "/v1/projects/{project}/modules",
      "auth": "product",
      "pathParams": [
        "project"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "bytes_base64"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "bytes_base64"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call POST /v1/projects/{project}/modules."
    },
    {
      "id": "projectsModulesGet",
      "upstreamOperationId": "projects.modules.get",
      "method": "GET",
      "path": "/v1/projects/{project}/modules/{sha256}",
      "auth": "product",
      "pathParams": [
        "project",
        "sha256"
      ],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Call GET /v1/projects/{project}/modules/{sha256}."
    }
  ],
  "remi": [
    {
      "id": "livez",
      "upstreamOperationId": "livez",
      "method": "GET",
      "path": "/livez",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check memory-server liveness."
    },
    {
      "id": "readyz",
      "upstreamOperationId": "readyz",
      "method": "GET",
      "path": "/readyz",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check memory-server readiness, including database health."
    },
    {
      "id": "health",
      "upstreamOperationId": "health",
      "method": "GET",
      "path": "/v1/health",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch deep store health: schema version, integrity checks, and graph consistency."
    },
    {
      "id": "getStats",
      "upstreamOperationId": "getStats",
      "method": "GET",
      "path": "/v1/stats",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch memory-store statistics: ledger events, nodes, and token counts by kind."
    },
    {
      "id": "getMetrics",
      "upstreamOperationId": "getMetrics",
      "method": "GET",
      "path": "/v1/metrics",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch service metrics as JSON, including per-route counters and query-tier latencies."
    },
    {
      "id": "getPrometheusMetrics",
      "upstreamOperationId": "getPrometheusMetrics",
      "method": "GET",
      "path": "/v1/metrics/prometheus",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch service metrics in Prometheus text exposition format for scrape-based monitoring."
    },
    {
      "id": "listAudit",
      "upstreamOperationId": "listAudit",
      "method": "GET",
      "path": "/v1/audit",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List recent service audit events (default 100, maximum 500)."
    },
    {
      "id": "remember",
      "upstreamOperationId": "remember",
      "method": "POST",
      "path": "/v1/remember",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "tenant_id",
        "project_id",
        "environment_id",
        "kind",
        "text",
        "idempotency_key",
        "project"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "tenant_id",
        "project_id",
        "kind",
        "text"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Write one memory event into the tenant and project ledger."
    },
    {
      "id": "project",
      "upstreamOperationId": "project",
      "method": "POST",
      "path": "/v1/project",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "limit"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Project pending ledger events into the memory graph and return the projection report."
    },
    {
      "id": "query",
      "upstreamOperationId": "query",
      "method": "POST",
      "path": "/v1/query",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "question",
        "scope",
        "max_tokens",
        "require_fresh",
        "modes",
        "reconstruction_mode",
        "max_reconstruction_steps",
        "max_reconstruction_tokens"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "question",
        "scope"
      ],
      "bodyDefaults": {},
      "scope": null,
      "description": "Answer a scoped memory question with evidence and reconstruction metadata."
    },
    {
      "id": "maintenance",
      "upstreamOperationId": "maintenance",
      "method": "POST",
      "path": "/v1/maintenance",
      "auth": "product",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [
        "vacuum",
        "repair_orphans",
        "prune_audit_before_unix_ms",
        "retain_latest_audit_events"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Run store maintenance: optimize, checkpoint, and optionally vacuum, repair orphans, and prune audit history."
    }
  ],
  "dataEngine": [
    {
      "id": "health",
      "upstreamOperationId": "health.get",
      "method": "GET",
      "path": "/v1/health",
      "auth": "none",
      "pathParams": [],
      "pathParamTemplates": {},
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check data-engine liveness; returns the service status."
    },
    {
      "id": "listUseCases",
      "upstreamOperationId": "projects.useCases.list",
      "method": "GET",
      "path": "/v1/{parent}/use-cases",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List the MVP use-case templates (data products and pipeline templates) for a project."
    },
    {
      "id": "getUseCase",
      "upstreamOperationId": "projects.useCases.get",
      "method": "GET",
      "path": "/v1/{parent}/use-cases/{useCaseId}",
      "auth": "product",
      "pathParams": [
        "parent",
        "useCaseId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one MVP use-case template with its rubric, modalities, skill tags, and target accuracy."
    },
    {
      "id": "ingestArtifact",
      "upstreamOperationId": "projects.artifacts.ingest",
      "method": "POST",
      "path": "/v1/{parent}/artifacts:ingest",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "artifactType",
        "source",
        "externalId",
        "rawBody",
        "metadata"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Ingest one artifact deterministically into the project; returns an async operation handle."
    },
    {
      "id": "ingestWeb",
      "upstreamOperationId": "projects.web.ingest",
      "method": "POST",
      "path": "/v1/{parent}/web:ingest",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "url",
        "artifactType",
        "timeoutSeconds",
        "maxBytes",
        "producerVersion",
        "metadata"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "url"
      ],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Fetch, parse, and ingest one public HTTP(S) page as a web artifact; returns an async operation handle."
    },
    {
      "id": "createCampaign",
      "upstreamOperationId": "projects.campaigns.create",
      "method": "POST",
      "path": "/v1/{parent}/campaigns",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "taskFamily",
        "targetAccuracy",
        "budgetCents",
        "rubric",
        "skillTags",
        "requiredReviews",
        "qualificationPolicy",
        "routingPolicy",
        "annotationSchema",
        "idempotencyKey"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Create a data campaign with a rubric, budget, target accuracy, and skill tags."
    },
    {
      "id": "listCampaigns",
      "upstreamOperationId": "projects.campaigns.list",
      "method": "GET",
      "path": "/v1/{parent}/campaigns",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List a project's data campaigns with pagination."
    },
    {
      "id": "transitionCampaign",
      "upstreamOperationId": "projects.campaigns.transition",
      "method": "POST",
      "path": "/v1/{parent}/campaigns/{campaignId}:transition",
      "auth": "product",
      "pathParams": [
        "parent",
        "campaignId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "targetStatus",
        "idempotencyKey"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "targetStatus",
        "idempotencyKey"
      ],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Pause, resume, or permanently close campaign job admission; returns an immutable receipt for the committed lifecycle transition."
    },
    {
      "id": "getReviewerQualification",
      "upstreamOperationId": "projects.reviewerQualifications.get",
      "method": "GET",
      "path": "/v1/{parent}/campaigns/{campaignId}/reviewer-qualification",
      "auth": "product",
      "pathParams": [
        "parent",
        "campaignId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "review:resolve",
      "description": "Fetch the authenticated reviewer's project-scoped qualification and campaign eligibility without blind-probe outcomes."
    },
    {
      "id": "runUseCase",
      "upstreamOperationId": "projects.pipelines.runUseCase",
      "method": "POST",
      "path": "/v1/{parent}/pipelines:runUseCase",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "useCase",
        "verifier",
        "budgetCents",
        "targetAccuracy",
        "rubric",
        "skillTags",
        "requiredReviews",
        "urls",
        "artifacts"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "useCase"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Run a complete MVP use-case pipeline end to end; verifier selects the configured verification backend."
    },
    {
      "id": "listExpertTasks",
      "upstreamOperationId": "projects.expertTasks.list",
      "method": "GET",
      "path": "/v1/{parent}/expert-tasks",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "pageSize",
        "pageToken",
        "status",
        "campaignName"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List human residual review tasks, optionally filtered by status and campaign."
    },
    {
      "id": "createReviewQualificationTask",
      "upstreamOperationId": "projects.reviewQualificationTasks.create",
      "method": "POST",
      "path": "/v1/{parent}/review-qualification-tasks",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "sourceExpertTaskName",
        "expectedLabel",
        "mode",
        "feedbackPolicy",
        "idempotencyKey"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "sourceExpertTaskName",
        "expectedLabel",
        "idempotencyKey"
      ],
      "bodyDefaults": {},
      "scope": "review:gold:manage",
      "description": "Clone a review task into an isolated, HMAC-scored qualification task without returning the expected label."
    },
    {
      "id": "resolveExpertTask",
      "upstreamOperationId": "projects.expertTasks.resolve",
      "method": "POST",
      "path": "/v1/{parent}/expert-tasks/{expertTaskId}:resolve",
      "auth": "product",
      "pathParams": [
        "parent",
        "expertTaskId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "label",
        "outcome",
        "confidence",
        "rationale",
        "evidence",
        "annotation",
        "annotatorId",
        "idempotencyKey",
        "leaseToken",
        "reviewContext"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "label",
        "idempotencyKey",
        "reviewContext"
      ],
      "bodyDefaults": {},
      "scope": "review:resolve",
      "description": "Resolve, abstain, flag, or adjudicate one human residual with an idempotent normalized decision."
    },
    {
      "id": "claimExpertTask",
      "upstreamOperationId": "projects.expertTaskAssignments.claim",
      "method": "POST",
      "path": "/v1/{parent}/expert-tasks/{expertTaskId}:claim",
      "auth": "product",
      "pathParams": [
        "parent",
        "expertTaskId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "idempotencyKey",
        "leaseToken",
        "leaseDurationSeconds"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "idempotencyKey",
        "leaseToken"
      ],
      "bodyDefaults": {},
      "scope": "review:resolve",
      "description": "Atomically claim one open expert task with an exclusive renewable lease."
    },
    {
      "id": "renewExpertTaskAssignment",
      "upstreamOperationId": "projects.expertTaskAssignments.renew",
      "method": "POST",
      "path": "/v1/{parent}/expert-tasks/{expertTaskId}:renew",
      "auth": "product",
      "pathParams": [
        "parent",
        "expertTaskId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "idempotencyKey",
        "leaseToken",
        "leaseDurationSeconds"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "idempotencyKey",
        "leaseToken"
      ],
      "bodyDefaults": {},
      "scope": "review:resolve",
      "description": "Renew the authenticated reviewer's active expert-task lease."
    },
    {
      "id": "releaseExpertTaskAssignment",
      "upstreamOperationId": "projects.expertTaskAssignments.release",
      "method": "POST",
      "path": "/v1/{parent}/expert-tasks/{expertTaskId}:release",
      "auth": "product",
      "pathParams": [
        "parent",
        "expertTaskId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "idempotencyKey",
        "leaseToken"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "idempotencyKey",
        "leaseToken"
      ],
      "bodyDefaults": {},
      "scope": "review:resolve",
      "description": "Release the authenticated reviewer's active expert-task lease for reassignment."
    },
    {
      "id": "saveExpertTaskDraft",
      "upstreamOperationId": "projects.expertTaskAssignments.saveDraft",
      "method": "POST",
      "path": "/v1/{parent}/expert-tasks/{expertTaskId}:saveDraft",
      "auth": "product",
      "pathParams": [
        "parent",
        "expertTaskId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "idempotencyKey",
        "leaseToken",
        "draft",
        "expectedVersion"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "idempotencyKey",
        "leaseToken",
        "draft",
        "expectedVersion"
      ],
      "bodyDefaults": {},
      "scope": "review:resolve",
      "description": "Autosave a version-checked draft under the active reviewer lease."
    },
    {
      "id": "getReviewOperations",
      "upstreamOperationId": "projects.reviewOperations.get",
      "method": "GET",
      "path": "/v1/{parent}/review-operations",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "windowSeconds",
        "slaTargetSeconds"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "review:resolve",
      "description": "Fetch bounded project review-operations, SLA, agreement, calibration, rubric-drift, and budget observations."
    },
    {
      "id": "getMetrics",
      "upstreamOperationId": "projects.metrics.get",
      "method": "GET",
      "path": "/v1/{parent}/metrics",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch data-engine usage and quality metrics for a project."
    },
    {
      "id": "getLabelQuality",
      "upstreamOperationId": "projects.labelQuality.get",
      "method": "GET",
      "path": "/v1/{parent}/label-quality",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch the project label-quality report and unresolved expert backlog."
    },
    {
      "id": "getEcosystemReadiness",
      "upstreamOperationId": "projects.ecosystem.readiness.get",
      "method": "GET",
      "path": "/v1/{parent}/ecosystem/readiness",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch public-site and ecosystem readiness signals for a project."
    },
    {
      "id": "listArtifacts",
      "upstreamOperationId": "projects.artifacts.list",
      "method": "GET",
      "path": "/v1/{parent}/artifacts",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "pageSize",
        "pageToken",
        "view"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List a project's artifacts with cursor pagination, expanded to the requested view (BASIC or FULL)."
    },
    {
      "id": "getArtifact",
      "upstreamOperationId": "projects.artifacts.get",
      "method": "GET",
      "path": "/v1/{parent}/artifacts/{artifactId}",
      "auth": "product",
      "pathParams": [
        "parent",
        "artifactId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "view"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one artifact, expanded to the requested view (BASIC or FULL)."
    },
    {
      "id": "listArtifactLabels",
      "upstreamOperationId": "projects.artifacts.labels.list",
      "method": "GET",
      "path": "/v1/{parent}/artifacts/{artifactId}/labels",
      "auth": "product",
      "pathParams": [
        "parent",
        "artifactId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List the labels attached to one artifact."
    },
    {
      "id": "profileDataset",
      "upstreamOperationId": "projects.datasets.profile",
      "method": "POST",
      "path": "/v1/{parent}/datasets:profile",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "artifactIds",
        "artifactType"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Profile dataset quality before export, including duplicates, label coverage, and distributions."
    },
    {
      "id": "createJob",
      "upstreamOperationId": "projects.jobs.create",
      "method": "POST",
      "path": "/v1/{parent}/jobs",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "artifactIds",
        "taskFamily",
        "campaign",
        "targetAccuracy",
        "idempotencyKey",
        "verifier"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "artifactIds",
        "taskFamily"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Create an asynchronous labeling job over a set of artifacts; returns an operation handle to poll."
    },
    {
      "id": "getJob",
      "upstreamOperationId": "projects.jobs.get",
      "method": "GET",
      "path": "/v1/{parent}/jobs/{jobId}",
      "auth": "product",
      "pathParams": [
        "parent",
        "jobId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one labeling job with its state and progress."
    },
    {
      "id": "getJobResults",
      "upstreamOperationId": "projects.jobs.results.list",
      "method": "GET",
      "path": "/v1/{parent}/jobs/{jobId}/results",
      "auth": "product",
      "pathParams": [
        "parent",
        "jobId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List the deterministic label results a job produced."
    },
    {
      "id": "getProduct",
      "upstreamOperationId": "projects.products.get",
      "method": "GET",
      "path": "/v1/{parent}/products/{productId}",
      "auth": "product",
      "pathParams": [
        "parent",
        "productId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one emitted product bundle with its status and manifest URL."
    },
    {
      "id": "validateProduct",
      "upstreamOperationId": "projects.products.validate",
      "method": "POST",
      "path": "/v1/{parent}/products/{productId}:validate",
      "auth": "product",
      "pathParams": [
        "parent",
        "productId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Validate an emitted product bundle's referential integrity and hygiene."
    },
    {
      "id": "checkProductLeakage",
      "upstreamOperationId": "projects.products.checkLeakage",
      "method": "POST",
      "path": "/v1/{parent}/products:checkLeakage",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "productIds"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "productIds"
      ],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Check raw-hash leakage between exactly two product bundles."
    },
    {
      "id": "getProductManifest",
      "upstreamOperationId": "projects.products.manifest.get",
      "method": "GET",
      "path": "/v1/{parent}/products/{productId}/manifest",
      "auth": "product",
      "pathParams": [
        "parent",
        "productId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch an integrity-checked, bounded manifest for an emitted eval product."
    },
    {
      "id": "admitTrainingRelease",
      "upstreamOperationId": "projects.trainingReleases.admit",
      "method": "POST",
      "path": "/v1/{parent}/training-releases:admit",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "trainingProductId",
        "heldoutProductId",
        "idempotencyKey"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "trainingProductId",
        "heldoutProductId",
        "idempotencyKey"
      ],
      "bodyDefaults": {},
      "scope": "training:publish",
      "description": "Admit exact training and heldout product generations after revalidating integrity, review consent, and leakage constraints."
    },
    {
      "id": "getTrainingRelease",
      "upstreamOperationId": "projects.trainingReleases.get",
      "method": "GET",
      "path": "/v1/{parent}/training-releases/{releaseId}",
      "auth": "product",
      "pathParams": [
        "parent",
        "releaseId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "training:publish",
      "description": "Revalidate and fetch one training release, including any durable stale state."
    },
    {
      "id": "deriveBundle",
      "upstreamOperationId": "projects.products.derive",
      "method": "POST",
      "path": "/v1/{parent}/products/{productId}:derive",
      "auth": "product",
      "pathParams": [
        "parent",
        "productId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "format",
        "trainFraction",
        "includeRaw",
        "pageSize",
        "pageToken",
        "pairSources"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "format"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Derive a deterministic post-training bundle from a ready product."
    },
    {
      "id": "emitEval",
      "upstreamOperationId": "projects.products.emitEval",
      "method": "POST",
      "path": "/v1/{parent}/products:emitEval",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "artifactIds",
        "job"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "artifactIds",
        "job"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Emit an eval dataset bundle from verified artifacts; returns an async operation handle."
    },
    {
      "id": "extractSource",
      "upstreamOperationId": "projects.sources.extract",
      "method": "POST",
      "path": "/v1/{parent}/sources:extract",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "connector",
        "bucket",
        "prefix",
        "key",
        "maxObjects",
        "maxBytes",
        "statement",
        "limit",
        "soql",
        "maxPages",
        "artifactType",
        "source",
        "ingest",
        "metadata"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "connector"
      ],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Extract bounded objects or records from a configured source connector."
    },
    {
      "id": "listConnectors",
      "upstreamOperationId": "projects.connectors.list",
      "method": "GET",
      "path": "/v1/{parent}/connectors",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List registered source connectors for a project."
    },
    {
      "id": "createTool",
      "upstreamOperationId": "projects.tools.create",
      "method": "POST",
      "path": "/v1/{parent}/tools",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "name",
        "description",
        "inputSchema",
        "kind",
        "implementation",
        "createdBy"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "name",
        "description",
        "kind",
        "implementation"
      ],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Create or version-bump a stored custom tool."
    },
    {
      "id": "listTools",
      "upstreamOperationId": "projects.tools.list",
      "method": "GET",
      "path": "/v1/{parent}/tools",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List stored custom tools and their usage statistics."
    },
    {
      "id": "getTool",
      "upstreamOperationId": "projects.tools.get",
      "method": "GET",
      "path": "/v1/{parent}/tools/{toolName}",
      "auth": "product",
      "pathParams": [
        "parent",
        "toolName"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one stored custom tool and its usage statistics."
    },
    {
      "id": "deleteTool",
      "upstreamOperationId": "projects.tools.delete",
      "method": "DELETE",
      "path": "/v1/{parent}/tools/{toolName}",
      "auth": "product",
      "pathParams": [
        "parent",
        "toolName"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Delete a stored custom tool and every retained version."
    },
    {
      "id": "invokeTool",
      "upstreamOperationId": "projects.tools.invoke",
      "method": "POST",
      "path": "/v1/{parent}/tools/{toolName}:invoke",
      "auth": "product",
      "pathParams": [
        "parent",
        "toolName"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "arguments"
      ],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Invoke a stored custom tool through its configured execution boundary."
    },
    {
      "id": "projectsDiscoveryReleasesCommit",
      "upstreamOperationId": "projects.discoveryReleases.commit",
      "method": "POST",
      "path": "/v1/{parent}/discoveryReleases:commit",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "schemaVersion",
        "requestId",
        "releaseId",
        "releaseKind",
        "evidenceClass",
        "claimClass",
        "bindings",
        "lineageEdges",
        "budget",
        "eligibility",
        "prospectiveExecution"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "schemaVersion",
        "requestId",
        "releaseId",
        "releaseKind",
        "evidenceClass",
        "claimClass",
        "bindings",
        "lineageEdges",
        "budget",
        "eligibility",
        "prospectiveExecution"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Atomically commit an immutable discovery release graph."
    },
    {
      "id": "projectsDiscoveryReleasesGet",
      "upstreamOperationId": "projects.discoveryReleases.get",
      "method": "GET",
      "path": "/v1/{parent}/discoveryReleases/{discoveryReleaseId}",
      "auth": "product",
      "pathParams": [
        "parent",
        "discoveryReleaseId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Get one immutable discovery release."
    },
    {
      "id": "createEvidenceRecord",
      "upstreamOperationId": "projects.evidenceRecords.create",
      "method": "POST",
      "path": "/v1/{parent}/evidenceRecords",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "schemaVersion",
        "domain",
        "evidenceType",
        "payloadSchema",
        "payload",
        "sourceArtifactRefs",
        "artifactRefs",
        "verificationState",
        "verifierReceiptArtifactRefs",
        "qualityFlags",
        "provenance"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "schemaVersion",
        "domain",
        "evidenceType",
        "payloadSchema",
        "payload",
        "sourceArtifactRefs",
        "verificationState"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Create an immutable shared evidence record by canonical content hash."
    },
    {
      "id": "listEvidenceRecords",
      "upstreamOperationId": "projects.evidenceRecords.list",
      "method": "GET",
      "path": "/v1/{parent}/evidenceRecords",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "pageSize",
        "pageToken",
        "domain"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List immutable shared evidence records with bounded cursor pagination."
    },
    {
      "id": "getEvidenceRecord",
      "upstreamOperationId": "projects.evidenceRecords.get",
      "method": "GET",
      "path": "/v1/{parent}/evidenceRecords/{evidenceRecordId}",
      "auth": "product",
      "pathParams": [
        "parent",
        "evidenceRecordId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one immutable shared evidence record by its platform digest."
    },
    {
      "id": "createEpisode",
      "upstreamOperationId": "projects.episodes.create",
      "method": "POST",
      "path": "/v1/{parent}/episodes",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "schemaVersion",
        "domain",
        "contextEvidenceRef",
        "environmentRef",
        "seed",
        "observations",
        "toolCalls",
        "measuredOutcomes",
        "verifierResults",
        "rewardComponents",
        "terminalReason",
        "uncertainty",
        "provenance",
        "safetyEvents"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "schemaVersion",
        "domain",
        "contextEvidenceRef",
        "environmentRef",
        "seed",
        "observations",
        "measuredOutcomes",
        "verifierResults",
        "rewardComponents",
        "terminalReason"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Create an immutable shared episode by canonical content hash."
    },
    {
      "id": "listEpisodes",
      "upstreamOperationId": "projects.episodes.list",
      "method": "GET",
      "path": "/v1/{parent}/episodes",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "pageSize",
        "pageToken",
        "domain"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List immutable shared episodes with bounded cursor pagination."
    },
    {
      "id": "getEpisode",
      "upstreamOperationId": "projects.episodes.get",
      "method": "GET",
      "path": "/v1/{parent}/episodes/{episodeId}",
      "auth": "product",
      "pathParams": [
        "parent",
        "episodeId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one immutable shared episode by its platform digest."
    },
    {
      "id": "queryResearchRetrieval",
      "upstreamOperationId": "query_research_retrieval",
      "method": "POST",
      "path": "/v1/{parent}/researchRetrieval:query",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "contractVersion",
        "requestId",
        "obligation",
        "kinds",
        "epistemicStatuses",
        "checkerTrust",
        "includeEquivalent",
        "includeFailures",
        "under",
        "limit"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "contractVersion",
        "requestId",
        "obligation",
        "limit"
      ],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Retrieve deterministic candidates for one exact canonical typed research obligation."
    },
    {
      "id": "createResearchCatalogEntry",
      "upstreamOperationId": "projects.researchCatalogEntries.create",
      "method": "POST",
      "path": "/v1/{parent}/researchCatalogEntries",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [
        "kind",
        "version",
        "obligationHash",
        "capabilityRoute",
        "provenance",
        "tags",
        "contentHash"
      ],
      "forbiddenBody": [],
      "requiredBody": [
        "kind",
        "version",
        "obligationHash",
        "capabilityRoute",
        "provenance"
      ],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Create an immutable executable research catalog entry by canonical content hash."
    },
    {
      "id": "listResearchCatalogEntries",
      "upstreamOperationId": "projects.researchCatalogEntries.list",
      "method": "GET",
      "path": "/v1/{parent}/researchCatalogEntries",
      "auth": "product",
      "pathParams": [
        "parent"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [
        "pageSize",
        "pageToken"
      ],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List immutable executable research catalog entries with bounded pagination."
    },
    {
      "id": "getResearchCatalogEntry",
      "upstreamOperationId": "projects.researchCatalogEntries.get",
      "method": "GET",
      "path": "/v1/{parent}/researchCatalogEntries/{entryId}",
      "auth": "product",
      "pathParams": [
        "parent",
        "entryId"
      ],
      "pathParamTemplates": {
        "parent": "projects/*"
      },
      "query": [],
      "body": [],
      "forbiddenBody": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one immutable executable research catalog entry by content hash."
    }
  ]
}
);

export const TEMPERA_MCP_GATEWAY = Object.freeze(
{
  "description": "Unified MCP gateway at ${issuer}/mcp: stateless streamable-HTTP JSON-RPC 2.0, audience tempera-mcp with scope mcp:invoke. The model-facing surface is fixed to ten tempera_* fabric verbs; product capabilities are opaque, policy-filtered cards discovered with tempera_search, inspected with tempera_describe, and executed through tempera_invoke or tempera_prepare/tempera_commit. Per-call product execution is metered.",
  "methods": [
    {
      "id": "initialize",
      "rpc": "initialize",
      "description": "Open an MCP session and fetch server capabilities and instructions."
    },
    {
      "id": "ping",
      "rpc": "ping",
      "description": "Check gateway liveness over JSON-RPC."
    },
    {
      "id": "listTools",
      "rpc": "tools/list",
      "description": "List the fixed ten-verb Tempera capability-fabric surface; product cards never appear as flat product tool names."
    },
    {
      "id": "callTool",
      "rpc": "tools/call",
      "description": "Call a fixed fabric verb. Discover product cards with tempera_search, inspect a card with tempera_describe, then invoke its opaque capability reference through tempera_invoke or tempera_prepare/tempera_commit."
    },
    {
      "id": "whoami",
      "rpc": "tools/call",
      "tool": "tempera_whoami",
      "description": "Fetch the caller's identity, workspace, and scopes as seen by the gateway."
    },
    {
      "id": "status",
      "rpc": "tools/call",
      "tool": "tempera_status",
      "description": "Fetch gateway upstream health for every connected product MCP server."
    }
  ],
  "errorCodes": {
    "planLimit": -32002,
    "invalidRequest": -32600,
    "methodNotFound": -32601,
    "invalidParams": -32602,
    "internalError": -32603
  }
}
);
