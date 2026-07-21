// GENERATED FROM surface.json by scripts/gen-sdk-surface.py -- DO NOT EDIT BY HAND.
// The SDK surface tables: products, audiences, scopes, environments,
// the error contract, and every typed operation, shared verbatim with
// the Python and Rust packages.

export const TEMPERA_SURFACE_VERSION = 3;

export const TEMPERA_AUDIENCES = Object.freeze(["palette", "tempo", "cradle", "remi", "human-data", "data-engine", "tempera-mcp", "tempera-code", "tempera-llm", "tempera-workflows", "tempera-gym"]);
export const DEFAULT_AUDIENCE = "palette";
export const TEMPERA_SCOPES = Object.freeze(["mcp:invoke", "memory:read", "memory:write", "memory:manage", "trace:read", "trace:write", "dataset:read", "dataset:write", "eval:run", "training:publish", "review:resolve", "workflow:read", "workflow:write", "workflow:run", "model:read", "model:invoke", "pii:unmask", "admin"]);

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
    "temperaCodeApiUrl": "http://127.0.0.1:8789",
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
    "temperaCodeApiUrl": "https://preview-code-api.tempera.dev",
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
    "temperaCodeApiUrl": "https://staging-code-api.tempera.dev",
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
    "temperaCodeApiUrl": "https://code-api.tempera.dev",
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
  "temperaCode": {
    "name": "Tempera Code",
    "repository": "https://github.com/tempera-dev/tempera-code",
    "envVar": "TEMPERA_CODE_GATEWAY_URL",
    "audience": "tempera-code",
    "description": "Durable local workflow orchestration and hosted Responses-compatible inference through the Tempera Code gateway."
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
      "method": "GET",
      "path": "/healthz",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check control-plane liveness; returns {ok: true}."
    },
    {
      "id": "discovery",
      "method": "GET",
      "path": "/.well-known/oauth-authorization-server",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch OAuth 2.1 authorization-server metadata for the issuer."
    },
    {
      "id": "jwks",
      "method": "GET",
      "path": "/.well-known/jwks.json",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the JSON Web Key Set used to verify control-plane access tokens."
    },
    {
      "id": "protectedResourceMetadata",
      "method": "GET",
      "path": "/.well-known/oauth-protected-resource/{resource}",
      "auth": "none",
      "pathParams": [
        "resource"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch OAuth protected-resource metadata for one registered audience."
    },
    {
      "id": "signup",
      "method": "POST",
      "path": "/sessions",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [
        "email",
        "password",
        "organization",
        "invite_token"
      ],
      "requiredBody": [],
      "bodyDefaults": {
        "mode": "signup"
      },
      "scope": null,
      "description": "Create a Tempera account (or accept an invite) and receive an account-session token pair."
    },
    {
      "id": "login",
      "method": "POST",
      "path": "/sessions",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [
        "email",
        "password"
      ],
      "requiredBody": [],
      "bodyDefaults": {
        "mode": "login"
      },
      "scope": null,
      "description": "Log in with email and password and receive an account-session token pair."
    },
    {
      "id": "me",
      "method": "GET",
      "path": "/me",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the authenticated user's identity, active workspace, and roles."
    },
    {
      "id": "selectWorkspace",
      "method": "POST",
      "path": "/workspace/select",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [
        "org_id",
        "project_id",
        "environment_id"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Switch the active workspace and receive a token pair scoped to it."
    },
    {
      "id": "listOrgs",
      "method": "GET",
      "path": "/orgs",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List the organizations the authenticated user belongs to."
    },
    {
      "id": "createOrg",
      "method": "POST",
      "path": "/orgs",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [
        "name"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Create an organization; the caller becomes its owner."
    },
    {
      "id": "listProjects",
      "method": "GET",
      "path": "/projects",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List projects across every organization the user belongs to."
    },
    {
      "id": "createProject",
      "method": "POST",
      "path": "/projects",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [
        "org_id",
        "name"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Create a project in an organization (requires an org admin role)."
    },
    {
      "id": "listEnvironments",
      "method": "GET",
      "path": "/environments",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List environments across every project the user can access."
    },
    {
      "id": "createEnvironment",
      "method": "POST",
      "path": "/environments",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [
        "project_id",
        "name"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Create an environment in a project (requires an org admin role)."
    },
    {
      "id": "listTeamMembers",
      "method": "GET",
      "path": "/team/members",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List team members of the active organization."
    },
    {
      "id": "updateTeamMember",
      "method": "PATCH",
      "path": "/team/members/{member_id}",
      "auth": "account",
      "pathParams": [
        "member_id"
      ],
      "query": [],
      "body": [
        "role"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Change a team member's role (requires an org admin role; at least one owner must remain)."
    },
    {
      "id": "removeTeamMember",
      "method": "DELETE",
      "path": "/team/members/{member_id}",
      "auth": "account",
      "pathParams": [
        "member_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Remove a team member from the active organization (idempotent)."
    },
    {
      "id": "listInvites",
      "method": "GET",
      "path": "/invites",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List invites for the active organization, newest first."
    },
    {
      "id": "createInvite",
      "method": "POST",
      "path": "/invites",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [
        "email",
        "role"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Invite a user to the active organization; the accept URL is returned once."
    },
    {
      "id": "cancelInvite",
      "method": "DELETE",
      "path": "/invites/{invite_id}",
      "auth": "account",
      "pathParams": [
        "invite_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Cancel a pending invite (idempotent)."
    },
    {
      "id": "listApiKeys",
      "method": "GET",
      "path": "/api-keys",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List API keys in the active workspace; secrets are never returned."
    },
    {
      "id": "createApiKey",
      "method": "POST",
      "path": "/api-keys",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [
        "scopes",
        "audience",
        "org_id",
        "project_id",
        "environment_id"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Mint a workspace API key (tp_...); the secret is returned exactly once. The workspace ids must match the token's workspace."
    },
    {
      "id": "rotateApiKey",
      "method": "POST",
      "path": "/api-keys/{api_key_id}/rotate",
      "auth": "account",
      "pathParams": [
        "api_key_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Rotate an API key's secret; the new secret is returned exactly once."
    },
    {
      "id": "revokeApiKey",
      "method": "DELETE",
      "path": "/api-keys/{api_key_id}",
      "auth": "account",
      "pathParams": [
        "api_key_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Revoke an API key (idempotent)."
    },
    {
      "id": "listGrants",
      "method": "GET",
      "path": "/oauth/grants",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List the OAuth grants the user has approved in the active workspace."
    },
    {
      "id": "revokeGrant",
      "method": "DELETE",
      "path": "/oauth/grants/{grant_id}",
      "auth": "account",
      "pathParams": [
        "grant_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Revoke an OAuth grant and every refresh token issued under it."
    },
    {
      "id": "listSessions",
      "method": "GET",
      "path": "/sessions",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List the user's active account sessions."
    },
    {
      "id": "revokeSession",
      "method": "DELETE",
      "path": "/sessions/{session_id}",
      "auth": "account",
      "pathParams": [
        "session_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Revoke an account session and its tokens immediately (idempotent)."
    },
    {
      "id": "listConnectors",
      "method": "GET",
      "path": "/connectors",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List the connector catalog (MCP clients, editors, and API surfaces)."
    },
    {
      "id": "getConnectorStatus",
      "method": "GET",
      "path": "/connectors/{connector_id}/status",
      "auth": "account",
      "pathParams": [
        "connector_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch one connector's connection status for the active workspace."
    },
    {
      "id": "listProducts",
      "method": "GET",
      "path": "/products",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List the product catalog with default scopes and setup paths."
    },
    {
      "id": "getProductStatus",
      "method": "GET",
      "path": "/products/{product_id}/status",
      "auth": "account",
      "pathParams": [
        "product_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch one product's activation status, entitlements, signals, and usage meters."
    },
    {
      "id": "getModelCatalog",
      "method": "GET",
      "path": "/model-catalog",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "model:read",
      "description": "List the entitled Tempera Code model catalog; requires a tempera-code bearer with model:read and the model-gateway entitlement."
    },
    {
      "id": "getBillingStatus",
      "method": "GET",
      "path": "/billing/status",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the organization's plan, subscription, usage meters, entitlements, invoices, and pricing (requires a billing role)."
    },
    {
      "id": "createBillingCheckout",
      "method": "GET",
      "path": "/billing/checkout",
      "auth": "account",
      "pathParams": [],
      "query": [
        "rail",
        "plan_id",
        "billing_interval",
        "currency",
        "network"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Create a checkout handoff URL for a plan on the chosen payment rail (requires a billing role)."
    },
    {
      "id": "getBillingPortal",
      "method": "GET",
      "path": "/billing/portal",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the billing-portal URL for the organization (requires a billing role)."
    },
    {
      "id": "recordUsage",
      "method": "POST",
      "path": "/usage/events",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [
        "metric",
        "quantity",
        "org_id",
        "project_id",
        "environment_id"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Record a usage event against a metered plan limit; requires a token carrying the meter's product scope and returns the updated meter."
    },
    {
      "id": "listAuditLog",
      "method": "GET",
      "path": "/audit-log",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List recent audit-log events for the user and active organization (up to 50, newest first)."
    },
    {
      "id": "introspectToken",
      "method": "POST",
      "path": "/oauth/introspect",
      "auth": "introspectionSecret",
      "pathParams": [],
      "query": [],
      "body": [
        "token"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Introspect a token or tp_ API key server-side; requires the introspection secret and returns {active: false} for anything invalid."
    }
  ],
  "palette": [
    {
      "id": "health",
      "method": "GET",
      "path": "/health",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check palette API liveness; returns {ok: true}."
    },
    {
      "id": "listTraces",
      "method": "GET",
      "path": "/v1/traces/{tenant_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id"
      ],
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
        "limit",
        "cursor"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:read",
      "description": "List trace summaries for a tenant with filters and cursor pagination."
    },
    {
      "id": "getTrace",
      "method": "GET",
      "path": "/v1/traces/{tenant_id}/{trace_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "trace_id"
      ],
      "query": [
        "unmask",
        "reason"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:read",
      "description": "Fetch one full trace with all canonical spans; unmasking PII requires the pii:unmask scope and a reason."
    },
    {
      "id": "getSpan",
      "method": "GET",
      "path": "/v1/spans/{tenant_id}/{trace_id}/{span_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "trace_id",
        "span_id"
      ],
      "query": [
        "unmask",
        "reason"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:read",
      "description": "Fetch one canonical span by trace and span id."
    },
    {
      "id": "getSpanIo",
      "method": "GET",
      "path": "/v1/spans/{tenant_id}/{trace_id}/{span_id}/io",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "trace_id",
        "span_id"
      ],
      "query": [
        "unmask",
        "reason"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:read",
      "description": "Fetch a span's recorded input and output values."
    },
    {
      "id": "searchSpans",
      "method": "GET",
      "path": "/v1/search/{tenant_id}/spans",
      "auth": "product",
      "pathParams": [
        "tenant_id"
      ],
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
        "limit"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:read",
      "description": "Search spans by text query and facet filters."
    },
    {
      "id": "ingestSpan",
      "method": "POST",
      "path": "/v1/traces/native",
      "auth": "product",
      "pathParams": [],
      "query": [
        "durability"
      ],
      "body": [
        "scope",
        "trace_id",
        "span_id",
        "kind",
        "name",
        "status",
        "seq",
        "attributes",
        "redaction_class",
        "parent_span_id",
        "start_time",
        "end_time",
        "input",
        "output",
        "model",
        "tokens",
        "cost",
        "idempotency_key"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:write",
      "description": "Ingest one native span; idempotent when an idempotency key is supplied."
    },
    {
      "id": "importSource",
      "method": "POST",
      "path": "/v1/import/{tenant_id}/{project_id}/{environment_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "environment_id"
      ],
      "query": [
        "durability"
      ],
      "body": [
        "source",
        "payload"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:write",
      "description": "Import spans from a named external source payload."
    },
    {
      "id": "archiveTrace",
      "method": "POST",
      "path": "/v1/archive/{tenant_id}/{project_id}/{trace_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "trace_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "trace:read",
      "description": "Archive a trace to Parquet and return the archive manifest."
    },
    {
      "id": "createDataset",
      "method": "POST",
      "path": "/v1/datasets/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "query": [],
      "body": [
        "name"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Create a dataset for curating cases from traces."
    },
    {
      "id": "promoteTraceToCase",
      "method": "POST",
      "path": "/v1/datasets/{tenant_id}/{project_id}/{dataset_id}/cases/from-trace",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "dataset_id"
      ],
      "query": [],
      "body": [
        "trace_id",
        "span_id",
        "reference"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Promote a trace (or one span of it) into a dataset case."
    },
    {
      "id": "createDatasetVersion",
      "method": "POST",
      "path": "/v1/datasets/{tenant_id}/{project_id}/{dataset_id}/versions",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "dataset_id"
      ],
      "query": [],
      "body": [
        "case_ids"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Snapshot a dataset into an immutable version for evals and experiments."
    },
    {
      "id": "createApiKey",
      "method": "POST",
      "path": "/v1/api-keys/{tenant_id}/{project_id}/{environment_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "environment_id"
      ],
      "query": [],
      "body": [
        "scopes"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "admin",
      "description": "Mint a palette-scoped API key; the secret is returned exactly once."
    },
    {
      "id": "revokeApiKey",
      "method": "POST",
      "path": "/v1/api-keys/{tenant_id}/{project_id}/{environment_id}/{api_key_id}/revoke",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id",
        "environment_id",
        "api_key_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "admin",
      "description": "Revoke a palette API key."
    },
    {
      "id": "getUsageSummary",
      "method": "GET",
      "path": "/v1/usage/{tenant_id}/{project_id}",
      "auth": "product",
      "pathParams": [
        "tenant_id",
        "project_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "admin",
      "description": "Fetch usage totals for a tenant project."
    }
  ],
  "tempo": [
    {
      "id": "health",
      "method": "GET",
      "path": "/health",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check tempod liveness; returns {ok: true}."
    },
    {
      "id": "ready",
      "method": "GET",
      "path": "/ready",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check tempod readiness, including engine attachment, drain state, and session capacity."
    },
    {
      "id": "openapi",
      "method": "GET",
      "path": "/openapi.json",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch tempod's OpenAPI document, generated at runtime for this host."
    },
    {
      "id": "listSessions",
      "method": "GET",
      "path": "/sessions",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List browser sessions with their state and creation time."
    },
    {
      "id": "createSession",
      "method": "POST",
      "path": "/sessions",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "url",
        "driverless"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Open a browser session at a URL; driverless sessions skip engine attachment."
    },
    {
      "id": "closeSession",
      "method": "DELETE",
      "path": "/sessions/{session_id}",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Close a browser session and release its engine resources."
    },
    {
      "id": "observe",
      "method": "GET",
      "path": "/sessions/{session_id}/observe",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the session's compiled structured observation (ranked, stably-identified elements)."
    },
    {
      "id": "actBatch",
      "method": "POST",
      "path": "/sessions/{session_id}/act_batch",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "query": [],
      "body": [
        "batch",
        "input_tainted",
        "confirmed",
        "idempotency_key",
        "confirmation_grant",
        "payment_context"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Apply a batch of semantic actions with policy gating; returns the applied diff or a policy decision."
    },
    {
      "id": "screenshot",
      "method": "GET",
      "path": "/sessions/{session_id}/screenshot",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "query": [
        "set_of_marks"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Capture a PNG screenshot of the session, optionally annotated with set-of-marks."
    },
    {
      "id": "sessionEvents",
      "method": "GET",
      "path": "/sessions/{session_id}/events",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "query": [
        "after_seq"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the session's event window after a sequence number."
    },
    {
      "id": "adoptSession",
      "method": "POST",
      "path": "/sessions/{session_id}/adopt",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Let a human surface take write ownership of the session and receive an adoption lease."
    },
    {
      "id": "handoffSession",
      "method": "POST",
      "path": "/sessions/{session_id}/handoff",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Return write ownership of the session to the agent plane."
    },
    {
      "id": "createRun",
      "method": "POST",
      "path": "/sessions/{session_id}/runs",
      "auth": "product",
      "pathParams": [
        "session_id"
      ],
      "query": [],
      "body": [
        "goal",
        "actions",
        "max_rounds",
        "token_budget"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Start an agent run against the session with a goal, action budget, and round limit."
    },
    {
      "id": "listRuns",
      "method": "GET",
      "path": "/runs",
      "auth": "product",
      "pathParams": [],
      "query": [
        "session_id"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List agent runs, optionally filtered to one session."
    },
    {
      "id": "getRun",
      "method": "GET",
      "path": "/runs/{run_id}",
      "auth": "product",
      "pathParams": [
        "run_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch one agent run with its state."
    },
    {
      "id": "cancelRun",
      "method": "POST",
      "path": "/runs/{run_id}/cancel",
      "auth": "product",
      "pathParams": [
        "run_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Cancel an agent run."
    },
    {
      "id": "resumeRun",
      "method": "POST",
      "path": "/runs/{run_id}/resume",
      "auth": "product",
      "pathParams": [
        "run_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Resume an agent run after a human handoff completes."
    },
    {
      "id": "grantConfirmation",
      "method": "POST",
      "path": "/sessions/{session_id}/confirmations/{confirmation_id}",
      "auth": "product",
      "pathParams": [
        "session_id",
        "confirmation_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Grant a pending policy confirmation and receive a single-use grant token."
    }
  ],
  "temperaCode": [
    {
      "id": "health",
      "method": "GET",
      "path": "/healthz",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check Tempera Code gateway liveness."
    },
    {
      "id": "listModels",
      "method": "GET",
      "path": "/v1/models",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "model:read",
      "description": "List the entitled Tempera Code hosted model catalog."
    },
    {
      "id": "createResponse",
      "method": "POST",
      "path": "/v1/responses",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "model",
        "input",
        "instructions",
        "tools",
        "text"
      ],
      "requiredBody": [
        "model",
        "input"
      ],
      "bodyDefaults": {},
      "scope": "model:invoke",
      "description": "Create a non-streaming Responses-compatible inference request through the Tempera Code gateway."
    }
  ],
  "temperaLlm": [
    {
      "id": "health",
      "method": "GET",
      "path": "/healthz",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check tempera-llm gateway liveness; returns {ok: true}."
    },
    {
      "id": "listModels",
      "method": "GET",
      "path": "/v1/models",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "model:read",
      "description": "List the configured model catalog the gateway can route to."
    },
    {
      "id": "createChatCompletion",
      "method": "POST",
      "path": "/v1/chat/completions",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "model",
        "messages",
        "max_tokens",
        "temperature",
        "stream",
        "byok"
      ],
      "requiredBody": [
        "model",
        "messages"
      ],
      "bodyDefaults": {},
      "scope": "model:invoke",
      "description": "Create a non-streaming OpenAI-compatible chat completion through the tempera-llm gateway."
    },
    {
      "id": "createResponse",
      "method": "POST",
      "path": "/v1/responses",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "model",
        "input",
        "max_output_tokens",
        "byok"
      ],
      "requiredBody": [
        "model",
        "input"
      ],
      "bodyDefaults": {},
      "scope": "model:invoke",
      "description": "Create a non-streaming OpenAI Responses-style inference request through the tempera-llm gateway."
    }
  ],
  "temperaWorkflows": [
    {
      "id": "health",
      "method": "GET",
      "path": "/healthz",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check tempera-workflows engine liveness."
    },
    {
      "id": "listNodeTypes",
      "method": "GET",
      "path": "/v1/node-types",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:read",
      "description": "List the typed node catalog: native orchestration nodes plus the sdk.<product>.<operation> nodes generated from the SDK surface."
    },
    {
      "id": "listWorkflows",
      "method": "GET",
      "path": "/v1/workflows",
      "auth": "product",
      "pathParams": [],
      "query": [
        "limit"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:read",
      "description": "List stored workflow definitions, newest first."
    },
    {
      "id": "createWorkflow",
      "method": "POST",
      "path": "/v1/workflows",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "contractVersion",
        "id",
        "name",
        "description",
        "nodes",
        "edges",
        "settings"
      ],
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
      "method": "GET",
      "path": "/v1/workflows/{workflow_id}",
      "auth": "product",
      "pathParams": [
        "workflow_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:read",
      "description": "Fetch one stored workflow definition."
    },
    {
      "id": "updateWorkflow",
      "method": "PUT",
      "path": "/v1/workflows/{workflow_id}",
      "auth": "product",
      "pathParams": [
        "workflow_id"
      ],
      "query": [],
      "body": [
        "contractVersion",
        "id",
        "name",
        "description",
        "nodes",
        "edges",
        "settings"
      ],
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
      "id": "deleteWorkflow",
      "method": "DELETE",
      "path": "/v1/workflows/{workflow_id}",
      "auth": "product",
      "pathParams": [
        "workflow_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:write",
      "description": "Delete a stored workflow definition."
    },
    {
      "id": "validateWorkflow",
      "method": "POST",
      "path": "/v1/workflows:validate",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "contractVersion",
        "id",
        "name",
        "description",
        "nodes",
        "edges",
        "settings"
      ],
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
    },
    {
      "id": "composeWorkflow",
      "method": "POST",
      "path": "/v1/workflows/{workflow_id}:compose",
      "auth": "product",
      "pathParams": [
        "workflow_id"
      ],
      "query": [],
      "body": [
        "prompt",
        "draft",
        "history",
        "attachments",
        "model"
      ],
      "requiredBody": [
        "prompt"
      ],
      "bodyDefaults": {},
      "scope": "workflow:write",
      "description": "Search the full SDK-backed node catalog or ask Tempera Code to propose a validated workflow draft without saving or running it."
    },
    {
      "id": "assistJson",
      "method": "POST",
      "path": "/v1/workflows:assistJson",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "mode",
        "purpose",
        "expectedRoot",
        "context",
        "current",
        "prompt"
      ],
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
      "id": "createRun",
      "method": "POST",
      "path": "/v1/workflows/{workflow_id}/runs",
      "auth": "product",
      "pathParams": [
        "workflow_id"
      ],
      "query": [],
      "body": [
        "input",
        "idempotencyKey"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:run",
      "description": "Start a run of a stored workflow with an optional input document and idempotency key."
    },
    {
      "id": "callWorkflow",
      "method": "POST",
      "path": "/v1/workflows/{workflow_id}:call",
      "auth": "product",
      "pathParams": [
        "workflow_id"
      ],
      "query": [],
      "body": [
        "input",
        "idempotencyKey",
        "usePinned",
        "startAt",
        "only",
        "seedOutputs",
        "waitMs"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:run",
      "description": "Run a workflow to completion and return its output in a single call."
    },
    {
      "id": "listRuns",
      "method": "GET",
      "path": "/v1/runs",
      "auth": "product",
      "pathParams": [],
      "query": [
        "workflowId",
        "limit"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:read",
      "description": "List workflow runs, optionally filtered to one workflow."
    },
    {
      "id": "getRun",
      "method": "GET",
      "path": "/v1/runs/{run_id}",
      "auth": "product",
      "pathParams": [
        "run_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:read",
      "description": "Fetch one workflow run with its state, node results, and timings; the live SSE event stream at /v1/runs/{run_id}/events is passthrough-only."
    },
    {
      "id": "cancelRun",
      "method": "POST",
      "path": "/v1/runs/{run_id}:cancel",
      "auth": "product",
      "pathParams": [
        "run_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "workflow:run",
      "description": "Cancel a queued or running workflow run."
    }
  ],
  "temperaGym": [
    {
      "id": "health",
      "method": "GET",
      "path": "/healthz",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check tempera-gym service liveness."
    },
    {
      "id": "listEnvironments",
      "method": "GET",
      "path": "/v1/environments",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List the gym pack's environment catalog, including implementation status and per-environment manifests."
    },
    {
      "id": "listRuns",
      "method": "GET",
      "path": "/v1/runs",
      "auth": "product",
      "pathParams": [],
      "query": [
        "environment_id",
        "limit"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List persisted rollout run index records, newest first."
    },
    {
      "id": "getRun",
      "method": "GET",
      "path": "/v1/runs/{run}",
      "auth": "product",
      "pathParams": [
        "run"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one persisted run's index record and verified trajectory-v1 envelope by run id or trajectory content hash."
    },
    {
      "id": "createRollout",
      "method": "POST",
      "path": "/v1/rollouts",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "environment_id",
        "policy",
        "seed",
        "max_steps",
        "model"
      ],
      "requiredBody": [
        "environment_id",
        "seed"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Execute one rollout synchronously, persist the trajectory, and return the completed operation envelope."
    }
  ],
  "cradle": [
    {
      "id": "health",
      "method": "GET",
      "path": "/v1/health",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check sandbox-daemon liveness; returns status, version, and uptime."
    },
    {
      "id": "getCapabilities",
      "method": "GET",
      "path": "/v1/capabilities",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the sandbox capability matrix: lanes, engines, limits, and integrations."
    },
    {
      "id": "getIntegrationContract",
      "method": "GET",
      "path": "/v1/integration",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the ecosystem integration contract this daemon implements."
    },
    {
      "id": "execute",
      "method": "POST",
      "path": "/v1/execute",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "lane",
        "source",
        "entrypoint",
        "input",
        "stdin",
        "policy",
        "idempotency_key"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Execute source synchronously in a sandbox lane and return the result with metrics."
    },
    {
      "id": "createJob",
      "method": "POST",
      "path": "/v1/jobs",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "lane",
        "source",
        "entrypoint",
        "input",
        "stdin",
        "policy",
        "idempotency_key"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Submit an asynchronous sandbox job; returns an operation handle to poll."
    },
    {
      "id": "getJob",
      "method": "GET",
      "path": "/v1/jobs/{job_id}",
      "auth": "product",
      "pathParams": [
        "job_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch a sandbox job's status and result."
    },
    {
      "id": "cancelJob",
      "method": "DELETE",
      "path": "/v1/jobs/{job_id}",
      "auth": "product",
      "pathParams": [
        "job_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Cancel a queued or running sandbox job (idempotent for already-cancelled jobs)."
    },
    {
      "id": "getBrowserProfiles",
      "method": "GET",
      "path": "/v1/browser/profiles",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the browser sandbox profile levels and suppression modes this daemon offers."
    },
    {
      "id": "admitBrowserSession",
      "method": "POST",
      "path": "/v1/browser/admit",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "actor",
        "requested_level",
        "sensitivity",
        "allow_downgrade",
        "artifact_mode",
        "credential_mode",
        "required_controls",
        "sensitive_activity_mode",
        "target_origins",
        "task_label"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Request admission for a browser session at a sandbox level and receive the guard plan."
    },
    {
      "id": "getBrowserAdapterContract",
      "method": "GET",
      "path": "/v1/browser/adapter/contract",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch the browser adapter contract, required controls, and conformance profile."
    }
  ],
  "remi": [
    {
      "id": "livez",
      "method": "GET",
      "path": "/livez",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check memory-server liveness."
    },
    {
      "id": "readyz",
      "method": "GET",
      "path": "/readyz",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check memory-server readiness, including database health."
    },
    {
      "id": "health",
      "method": "GET",
      "path": "/v1/health",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch deep store health: schema version, integrity checks, and graph consistency."
    },
    {
      "id": "getStats",
      "method": "GET",
      "path": "/v1/stats",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch memory-store statistics: ledger events, nodes, and token counts by kind."
    },
    {
      "id": "getMetrics",
      "method": "GET",
      "path": "/v1/metrics",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch service metrics as JSON, including per-route counters and query-tier latencies."
    },
    {
      "id": "getPrometheusMetrics",
      "method": "GET",
      "path": "/v1/metrics/prometheus",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch service metrics in Prometheus text exposition format for scrape-based monitoring."
    },
    {
      "id": "listAudit",
      "method": "GET",
      "path": "/v1/audit",
      "auth": "product",
      "pathParams": [],
      "query": [
        "limit"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "List recent service audit events (default 100, maximum 500)."
    },
    {
      "id": "remember",
      "method": "POST",
      "path": "/v1/remember",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "tenant_id",
        "project_id",
        "kind",
        "text",
        "environment_id",
        "idempotency_key",
        "project"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Write one memory into the ledger and, by default, project it into the memory graph immediately."
    },
    {
      "id": "project",
      "method": "POST",
      "path": "/v1/project",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "limit"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Project pending ledger events into the memory graph and return the projection report."
    },
    {
      "id": "manage",
      "method": "POST",
      "path": "/v1/manage",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "limit"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Run memory management over pending ledger events (same engine pass as project, tracked separately)."
    },
    {
      "id": "query",
      "method": "POST",
      "path": "/v1/query",
      "auth": "product",
      "pathParams": [],
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
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Answer a question from memory with evidence, citations, contradictions, and staleness signals."
    },
    {
      "id": "maintenance",
      "method": "POST",
      "path": "/v1/maintenance",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [
        "vacuum",
        "repair_orphans",
        "prune_audit_before_unix_ms",
        "retain_latest_audit_events"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Run store maintenance: optimize, checkpoint, and optionally vacuum, repair orphans, and prune audit history."
    }
  ],
  "dataEngine": [
    {
      "id": "health",
      "method": "GET",
      "path": "/v1/health",
      "auth": "none",
      "pathParams": [],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": null,
      "description": "Check data-engine liveness; returns the service status."
    },
    {
      "id": "admitTrainingRelease",
      "method": "POST",
      "path": "/v1/projects/{project_id}/training-releases:admit",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "training_product_id",
        "heldout_product_id",
        "idempotency_key"
      ],
      "requiredBody": [
        "training_product_id",
        "heldout_product_id",
        "idempotency_key"
      ],
      "bodyDefaults": {},
      "scope": "training:publish",
      "description": "Admit exact training and heldout product generations after revalidating integrity, review consent, and leakage constraints."
    },
    {
      "id": "getTrainingRelease",
      "method": "GET",
      "path": "/v1/projects/{project_id}/training-releases/{release_id}",
      "auth": "product",
      "pathParams": [
        "project_id",
        "release_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "training:publish",
      "description": "Revalidate and fetch one training release, including any durable stale state."
    },
    {
      "id": "createEvidenceRecord",
      "method": "POST",
      "path": "/v1/projects/{project_id}/evidenceRecords",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "schema_version",
        "domain",
        "evidence_type",
        "payload_schema",
        "payload",
        "source_artifact_refs",
        "artifact_refs",
        "verification_state",
        "verifier_receipt_artifact_refs",
        "quality_flags",
        "provenance"
      ],
      "requiredBody": [
        "schema_version",
        "domain",
        "evidence_type",
        "payload_schema",
        "payload",
        "source_artifact_refs",
        "verification_state"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Create an immutable shared evidence record by canonical content hash."
    },
    {
      "id": "listEvidenceRecords",
      "method": "GET",
      "path": "/v1/projects/{project_id}/evidenceRecords",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [
        "page_size",
        "page_token",
        "domain"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List immutable shared evidence records with bounded cursor pagination."
    },
    {
      "id": "getEvidenceRecord",
      "method": "GET",
      "path": "/v1/projects/{project_id}/evidenceRecords/{evidence_record_id}",
      "auth": "product",
      "pathParams": [
        "project_id",
        "evidence_record_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one immutable shared evidence record by its platform digest."
    },
    {
      "id": "createEpisode",
      "method": "POST",
      "path": "/v1/projects/{project_id}/episodes",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "schema_version",
        "domain",
        "context_evidence_ref",
        "environment_ref",
        "seed",
        "observations",
        "tool_calls",
        "measured_outcomes",
        "verifier_results",
        "reward_components",
        "terminal_reason",
        "uncertainty",
        "provenance",
        "safety_events"
      ],
      "requiredBody": [
        "schema_version",
        "domain",
        "context_evidence_ref",
        "environment_ref",
        "seed",
        "observations",
        "measured_outcomes",
        "verifier_results",
        "reward_components",
        "terminal_reason"
      ],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Create an immutable shared episode by canonical content hash."
    },
    {
      "id": "listEpisodes",
      "method": "GET",
      "path": "/v1/projects/{project_id}/episodes",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [
        "page_size",
        "page_token",
        "domain"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List immutable shared episodes with bounded cursor pagination."
    },
    {
      "id": "getEpisode",
      "method": "GET",
      "path": "/v1/projects/{project_id}/episodes/{episode_id}",
      "auth": "product",
      "pathParams": [
        "project_id",
        "episode_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one immutable shared episode by its platform digest."
    },
    {
      "id": "queryResearchRetrieval",
      "method": "POST",
      "path": "/v1/projects/{project_id}/researchRetrieval:query",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
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
      "method": "POST",
      "path": "/v1/projects/{project_id}/researchCatalogEntries",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
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
      "method": "GET",
      "path": "/v1/projects/{project_id}/researchCatalogEntries",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [
        "page_size",
        "page_token"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List immutable executable research catalog entries with bounded pagination."
    },
    {
      "id": "getResearchCatalogEntry",
      "method": "GET",
      "path": "/v1/projects/{project_id}/researchCatalogEntries/{entry_id}",
      "auth": "product",
      "pathParams": [
        "project_id",
        "entry_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one immutable executable research catalog entry by content hash."
    },
    {
      "id": "listConnectors",
      "method": "GET",
      "path": "/v1/projects/{project_id}/connectors",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [
        "page_size",
        "page_token"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List registered source connectors for a project."
    },
    {
      "id": "listUseCases",
      "method": "GET",
      "path": "/v1/projects/{project_id}/use-cases",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [
        "page_size",
        "page_token"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List the MVP use-case templates (data products and pipeline templates) for a project."
    },
    {
      "id": "getUseCase",
      "method": "GET",
      "path": "/v1/projects/{project_id}/use-cases/{use_case_id}",
      "auth": "product",
      "pathParams": [
        "project_id",
        "use_case_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one MVP use-case template with its rubric, modalities, skill tags, and target accuracy."
    },
    {
      "id": "ingestArtifact",
      "method": "POST",
      "path": "/v1/projects/{project_id}/artifacts:ingest",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "artifactType",
        "source",
        "external_id",
        "raw_body",
        "metadata"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Ingest one artifact deterministically into the project; returns an async operation handle."
    },
    {
      "id": "ingestWeb",
      "method": "POST",
      "path": "/v1/projects/{project_id}/web:ingest",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "url",
        "artifactType",
        "timeoutSeconds",
        "maxBytes",
        "allowPrivate",
        "metadata"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Fetch, parse, and ingest one public HTTP(S) page as a web artifact; returns an async operation handle."
    },
    {
      "id": "runUseCase",
      "method": "POST",
      "path": "/v1/projects/{project_id}/pipelines:run-use-case",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "use_case",
        "budget_cents",
        "target_accuracy",
        "urls",
        "artifacts",
        "verifier"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Run a complete MVP use-case pipeline end to end; verifier selects the configured verification backend."
    },
    {
      "id": "createCampaign",
      "method": "POST",
      "path": "/v1/projects/{project_id}/campaigns",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "task_family",
        "target_accuracy",
        "budget_cents",
        "rubric",
        "skill_tags"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Create a data campaign with a rubric, budget, target accuracy, and skill tags."
    },
    {
      "id": "listCampaigns",
      "method": "GET",
      "path": "/v1/projects/{project_id}/campaigns",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [
        "page_size",
        "page_token"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List a project's data campaigns with pagination."
    },
    {
      "id": "transitionCampaign",
      "method": "POST",
      "path": "/v1/projects/{project_id}/campaigns/{campaign_id}:transition",
      "auth": "product",
      "pathParams": [
        "project_id",
        "campaign_id"
      ],
      "query": [],
      "body": [
        "target_status",
        "idempotency_key"
      ],
      "requiredBody": [
        "target_status",
        "idempotency_key"
      ],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Pause, resume, or permanently close campaign job admission; returns an immutable receipt for the committed lifecycle transition."
    },
    {
      "id": "listArtifacts",
      "method": "GET",
      "path": "/v1/projects/{project_id}/artifacts",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [
        "page_size",
        "page_token",
        "view"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List a project's artifacts with cursor pagination, expanded to the requested view (BASIC or FULL)."
    },
    {
      "id": "getArtifact",
      "method": "GET",
      "path": "/v1/projects/{project_id}/artifacts/{artifact_id}",
      "auth": "product",
      "pathParams": [
        "project_id",
        "artifact_id"
      ],
      "query": [
        "view"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one artifact, expanded to the requested view (BASIC or FULL)."
    },
    {
      "id": "listArtifactLabels",
      "method": "GET",
      "path": "/v1/projects/{project_id}/artifacts/{artifact_id}/labels",
      "auth": "product",
      "pathParams": [
        "project_id",
        "artifact_id"
      ],
      "query": [
        "page_size",
        "page_token"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List the labels attached to one artifact."
    },
    {
      "id": "profileDataset",
      "method": "POST",
      "path": "/v1/projects/{project_id}/datasets:profile",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "artifact_ids",
        "artifact_type"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Profile dataset quality before export, including duplicates, label coverage, and distributions."
    },
    {
      "id": "createJob",
      "method": "POST",
      "path": "/v1/projects/{project_id}/jobs",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "artifact_ids",
        "task_family",
        "campaign",
        "target_accuracy",
        "verifier",
        "idempotency_key"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Create an asynchronous labeling job over a set of artifacts; returns an operation handle to poll."
    },
    {
      "id": "getJob",
      "method": "GET",
      "path": "/v1/projects/{project_id}/jobs/{job_id}",
      "auth": "product",
      "pathParams": [
        "project_id",
        "job_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one labeling job with its state and progress."
    },
    {
      "id": "getJobResults",
      "method": "GET",
      "path": "/v1/projects/{project_id}/jobs/{job_id}/results",
      "auth": "product",
      "pathParams": [
        "project_id",
        "job_id"
      ],
      "query": [
        "page_size",
        "page_token"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List the deterministic label results a job produced."
    },
    {
      "id": "listExpertTasks",
      "method": "GET",
      "path": "/v1/projects/{project_id}/expert-tasks",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [
        "page_size",
        "page_token",
        "status",
        "campaign_name"
      ],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List human residual review tasks, optionally filtered by status and campaign."
    },
    {
      "id": "resolveExpertTask",
      "method": "POST",
      "path": "/v1/projects/{project_id}/expert-tasks/{expert_task_id}:resolve",
      "auth": "product",
      "pathParams": [
        "project_id",
        "expert_task_id"
      ],
      "query": [],
      "body": [
        "label",
        "outcome",
        "confidence",
        "rationale",
        "evidence",
        "annotator_id",
        "idempotency_key",
        "review_context"
      ],
      "requiredBody": [
        "label",
        "idempotency_key",
        "review_context"
      ],
      "bodyDefaults": {},
      "scope": "review:resolve",
      "description": "Resolve, abstain, flag, or adjudicate one human residual with an idempotent normalized decision."
    },
    {
      "id": "getMetrics",
      "method": "GET",
      "path": "/v1/projects/{project_id}/metrics",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch data-engine usage and quality metrics for a project."
    },
    {
      "id": "getLabelQuality",
      "method": "GET",
      "path": "/v1/projects/{project_id}/label-quality",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch the project label-quality report and unresolved expert backlog."
    },
    {
      "id": "getEcosystemReadiness",
      "method": "GET",
      "path": "/v1/projects/{project_id}/ecosystem/readiness",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch public-site and ecosystem readiness signals for a project."
    },
    {
      "id": "emitEval",
      "method": "POST",
      "path": "/v1/projects/{project_id}/products:emit-eval",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "artifact_ids",
        "include_provenance",
        "license",
        "filters"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Emit an eval dataset bundle from verified artifacts; returns an async operation handle."
    },
    {
      "id": "deriveBundle",
      "method": "POST",
      "path": "/v1/projects/{project_id}/products/{product_id}:derive",
      "auth": "product",
      "pathParams": [
        "project_id",
        "product_id"
      ],
      "query": [],
      "body": [
        "format",
        "train_fraction",
        "include_raw",
        "page_size",
        "page_token",
        "pair_sources"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "eval:run",
      "description": "Derive a deterministic post-training bundle from a ready product."
    },
    {
      "id": "getProduct",
      "method": "GET",
      "path": "/v1/projects/{project_id}/products/{product_id}",
      "auth": "product",
      "pathParams": [
        "project_id",
        "product_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one emitted product bundle with its status and manifest URL."
    },
    {
      "id": "validateProduct",
      "method": "POST",
      "path": "/v1/projects/{project_id}/products/{product_id}:validate",
      "auth": "product",
      "pathParams": [
        "project_id",
        "product_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Validate an emitted product bundle's referential integrity and hygiene."
    },
    {
      "id": "checkProductLeakage",
      "method": "POST",
      "path": "/v1/projects/{project_id}/products:check-leakage",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "product_ids"
      ],
      "requiredBody": [
        "product_ids"
      ],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Check raw-hash leakage between exactly two product bundles."
    },
    {
      "id": "getProductManifest",
      "method": "GET",
      "path": "/v1/projects/{project_id}/products/{product_id}/manifest",
      "auth": "product",
      "pathParams": [
        "project_id",
        "product_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch an integrity-checked, bounded manifest for an emitted eval product."
    },
    {
      "id": "extractSource",
      "method": "POST",
      "path": "/v1/projects/{project_id}/sources:extract",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "connector",
        "bucket",
        "prefix",
        "key",
        "max_objects",
        "max_bytes",
        "statement",
        "limit",
        "soql",
        "max_pages",
        "artifact_type",
        "source",
        "ingest",
        "metadata"
      ],
      "requiredBody": [
        "connector"
      ],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Extract bounded objects or records from a configured source connector."
    },
    {
      "id": "createTool",
      "method": "POST",
      "path": "/v1/projects/{project_id}/tools",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [
        "name",
        "description",
        "input_schema",
        "kind",
        "implementation",
        "created_by"
      ],
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
      "method": "GET",
      "path": "/v1/projects/{project_id}/tools",
      "auth": "product",
      "pathParams": [
        "project_id"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "List stored custom tools and their usage statistics."
    },
    {
      "id": "getTool",
      "method": "GET",
      "path": "/v1/projects/{project_id}/tools/{tool_name}",
      "auth": "product",
      "pathParams": [
        "project_id",
        "tool_name"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:read",
      "description": "Fetch one stored custom tool and its usage statistics."
    },
    {
      "id": "deleteTool",
      "method": "DELETE",
      "path": "/v1/projects/{project_id}/tools/{tool_name}",
      "auth": "product",
      "pathParams": [
        "project_id",
        "tool_name"
      ],
      "query": [],
      "body": [],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Delete a stored custom tool and every retained version."
    },
    {
      "id": "invokeTool",
      "method": "POST",
      "path": "/v1/projects/{project_id}/tools/{tool_name}:invoke",
      "auth": "product",
      "pathParams": [
        "project_id",
        "tool_name"
      ],
      "query": [],
      "body": [
        "arguments"
      ],
      "requiredBody": [],
      "bodyDefaults": {},
      "scope": "dataset:write",
      "description": "Invoke a stored custom tool through its configured execution boundary."
    }
  ]
}
);

export const TEMPERA_MCP_GATEWAY = Object.freeze(
{
  "description": "Unified MCP gateway at ${issuer}/mcp: stateless streamable-HTTP JSON-RPC 2.0, audience tempera-mcp with scope mcp:invoke, aggregating product MCP servers behind namespaced tools (palette_*, tempo_*, cradle_*, remi_*, data_engine_*) with per-call billing.",
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
      "description": "List every tool the gateway offers: builtins plus namespaced product tools."
    },
    {
      "id": "callTool",
      "rpc": "tools/call",
      "description": "Invoke a tool by name; product tool calls are metered as mcp_invocations."
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
