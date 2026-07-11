// GENERATED FROM surface.json by scripts/gen-sdk-surface.py -- DO NOT EDIT BY HAND.
// The SDK surface tables: products, audiences, scopes, environments,
// the error contract, and every typed operation, shared verbatim with
// the Python and Rust packages.

export const TEMPERA_SURFACE_VERSION = 2;

export const TEMPERA_AUDIENCES = Object.freeze(["palette", "tempo", "cradle", "remi", "human-data", "tempera-mcp"]);
export const DEFAULT_AUDIENCE = "palette";
export const TEMPERA_SCOPES = Object.freeze(["mcp:invoke", "trace:read", "trace:write", "dataset:read", "dataset:write", "eval:run", "pii:unmask", "admin"]);

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
  "cradle": {
    "name": "cradle",
    "repository": "https://github.com/tempera-dev/cradle",
    "envVar": "TEMPERA_CRADLE_URL",
    "audience": "cradle",
    "description": "Capability sandbox daemon (beatbox): synchronous and job-based sandboxed execution plus browser admission control."
  },
  "remi": {
    "name": "remi",
    "repository": "https://github.com/tempera-dev/remi",
    "envVar": "TEMPERA_REMI_URL",
    "audience": "remi",
    "description": "Temporal memory server (beater-memory): remember, project, query, and maintain an agent memory graph."
  },
  "humanData": {
    "name": "human-data",
    "repository": "https://github.com/tempera-dev/human-data",
    "envVar": "TEMPERA_HUMAN_DATA_URL",
    "audience": "human-data",
    "description": "Human data operations: expert annotation and review pipelines. Passthrough client only; no typed operations yet."
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
      "bodyDefaults": {},
      "scope": null,
      "description": "Fetch one product's activation status, entitlements, signals, and usage meters."
    },
    {
      "id": "getBillingStatus",
      "method": "GET",
      "path": "/billing/status",
      "auth": "account",
      "pathParams": [],
      "query": [],
      "body": [],
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
      "bodyDefaults": {},
      "scope": null,
      "description": "Grant a pending policy confirmation and receive a single-use grant token."
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
      "bodyDefaults": {},
      "scope": null,
      "description": "Check beatbox liveness; returns status, version, and uptime."
    },
    {
      "id": "getCapabilities",
      "method": "GET",
      "path": "/v1/capabilities",
      "auth": "product",
      "pathParams": [],
      "query": [],
      "body": [],
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
      "bodyDefaults": {},
      "scope": null,
      "description": "Run store maintenance: optimize, checkpoint, and optionally vacuum, repair orphans, and prune audit history."
    }
  ]
}
);

export const TEMPERA_MCP_GATEWAY = Object.freeze(
{
  "description": "Unified MCP gateway at ${issuer}/mcp: stateless streamable-HTTP JSON-RPC 2.0, audience tempera-mcp with scope mcp:invoke, aggregating product MCP servers behind namespaced tools (palette_*, tempo_*, cradle_*, remi_*) with per-call billing.",
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
