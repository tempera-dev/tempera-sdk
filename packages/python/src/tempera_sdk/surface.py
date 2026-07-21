"""GENERATED FROM surface.json by scripts/gen-sdk-surface.py -- DO NOT EDIT BY HAND.

The SDK surface tables: products, audiences, scopes, environments, the
error contract, and every typed operation, shared verbatim with the
TypeScript and Rust packages.
"""

SURFACE_VERSION = 3

AUDIENCES = ('palette', 'tempo', 'cradle', 'remi', 'human-data', 'data-engine', 'tempera-mcp', 'tempera-code', 'tempera-llm', 'tempera-workflows', 'tempera-gym')
DEFAULT_AUDIENCE = 'palette'
SCOPES = ('mcp:invoke', 'memory:read', 'memory:write', 'memory:manage', 'trace:read', 'trace:write', 'dataset:read', 'dataset:write', 'eval:run', 'training:publish', 'review:resolve', 'workflow:read', 'workflow:write', 'workflow:run', 'model:read', 'model:invoke', 'pii:unmask', 'admin')

ISSUER_PATHS = {'authorize': '/oauth/authorize', 'token': '/oauth/token', 'revoke': '/oauth/revoke', 'introspect': '/oauth/introspect', 'mcp': '/mcp'}

ENVIRONMENTS = {
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

PRODUCTS = {
    "controlPlane": {
        "name": "auth-hub",
        "repository": "https://github.com/tempera-dev/auth-hub",
        "env_var": "TEMPERA_CONTROL_PLANE_URL",
        "audience": None,
        "description": "Tempera control plane: unified accounts, OAuth issuance, workspaces, teams, API keys, billing, usage metering, and the unified MCP gateway."
    },
    "palette": {
        "name": "palette",
        "repository": "https://github.com/tempera-dev/palette",
        "env_var": "TEMPERA_PALETTE_URL",
        "audience": "palette",
        "description": "Agent observability: trace and span ingestion, search, datasets, evals, experiments, gates, and human review."
    },
    "tempo": {
        "name": "tempo",
        "repository": "https://github.com/tempera-dev/tempo",
        "env_var": "TEMPERA_TEMPO_URL",
        "audience": "tempo",
        "description": "Agent-native browser daemon (tempod): structured observation, batched actions, sessions, runs, and human handoff."
    },
    "temperaCode": {
        "name": "Tempera Code",
        "repository": "https://github.com/tempera-dev/tempera-code",
        "env_var": "TEMPERA_CODE_GATEWAY_URL",
        "audience": "tempera-code",
        "description": "Durable local workflow orchestration and hosted Responses-compatible inference through the Tempera Code gateway."
    },
    "temperaLlm": {
        "name": "tempera-llm",
        "repository": "https://github.com/tempera-dev/tempera-llm",
        "env_var": "TEMPERA_LLM_URL",
        "audience": "tempera-llm",
        "description": "OpenAI-compatible LLM gateway every Tempera product calls instead of hitting providers directly; reports LLM cost as model_cost usage events per the billing-credits contract."
    },
    "temperaWorkflows": {
        "name": "tempera-workflows",
        "repository": "https://github.com/tempera-dev/tempera-workflows",
        "env_var": "TEMPERA_WORKFLOWS_URL",
        "audience": "tempera-workflows",
        "description": "Deterministic workflow engine: bounded-DAG workflows (tempera.workflow/v1) of typed nodes executed as replayable, event-streamed runs; the run event stream (GET /v1/runs/{run_id}/events, SSE) is reachable through the raw passthrough request only."
    },
    "temperaGym": {
        "name": "tempera-gym",
        "repository": "https://github.com/tempera-dev/tempera-gym",
        "env_var": "TEMPERA_GYM_URL",
        "audience": "tempera-gym",
        "description": "RL environment pack service: environment catalog with implementation status, synchronous rollout execution, and persisted content-addressed trajectory-v1 runs."
    },
    "cradle": {
        "name": "cradle",
        "repository": "https://github.com/tempera-dev/cradle",
        "env_var": "TEMPERA_CRADLE_URL",
        "audience": "cradle",
        "description": "Capability sandbox daemon (cradled): synchronous and job-based sandboxed execution plus browser admission control."
    },
    "remi": {
        "name": "remi",
        "repository": "https://github.com/tempera-dev/remi",
        "env_var": "TEMPERA_REMI_URL",
        "audience": "remi",
        "description": "Temporal memory server: remember, project, query, and maintain an agent memory graph."
    },
    "dataEngine": {
        "name": "data-engine",
        "repository": "https://github.com/tempera-dev/data-engine",
        "env_var": "TEMPERA_DATA_ENGINE_URL",
        "audience": "data-engine",
        "description": "Domain-portable label-emergence engine: deterministic ingestion, sandboxed verification in cradle, and RL/eval/SFT dataset emission."
    },
    "humanData": {
        "name": "human-data",
        "repository": "https://github.com/tempera-dev/human-data",
        "env_var": "TEMPERA_HUMAN_DATA_URL",
        "audience": "human-data",
        "description": "Browser-agent human review: reviewers inspect provisioned browser-session evidence, record decisions, and return candidate cases to the agent quality loop. Passthrough client only; no typed operations yet."
    },
    "tempJs": {
        "name": "temp.js",
        "repository": "https://github.com/tempera-dev/temp.js",
        "env_var": "TEMPERA_TEMPJS_URL",
        "audience": None,
        "description": "Durable JavaScript runtime bridge for Tempera agents. Passthrough client only; no typed operations yet."
    },
    "tempOS": {
        "name": "tempOS",
        "repository": "https://github.com/tempera-dev/tempOS",
        "env_var": "TEMPERA_TEMPOS_URL",
        "audience": None,
        "description": "OS/runtime admission, policy, and receipt layer for agents. Passthrough client only; no typed operations yet."
    },
    "arrha": {
        "name": "Arrha",
        "repository": "https://github.com/tempera-dev/arrha",
        "env_var": "TEMPERA_ARRHA_URL",
        "audience": None,
        "description": "Settlement, chain, credits, and indexer layer for agent payments. Passthrough client only; no typed operations yet."
    }
}

OPERATIONS = {
    "controlPlane": [
        {
            "id": "health",
            "method": "GET",
            "path": "/healthz",
            "auth": "none",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check control-plane liveness; returns {ok: True}."
        },
        {
            "id": "discovery",
            "method": "GET",
            "path": "/.well-known/oauth-authorization-server",
            "auth": "none",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch OAuth 2.1 authorization-server metadata for the issuer."
        },
        {
            "id": "jwks",
            "method": "GET",
            "path": "/.well-known/jwks.json",
            "auth": "none",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the JSON Web Key Set used to verify control-plane access tokens."
        },
        {
            "id": "protected_resource_metadata",
            "method": "GET",
            "path": "/.well-known/oauth-protected-resource/{resource}",
            "auth": "none",
            "path_params": [
                "resource"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch OAuth protected-resource metadata for one registered audience."
        },
        {
            "id": "signup",
            "method": "POST",
            "path": "/sessions",
            "auth": "none",
            "path_params": [],
            "query": [],
            "body": [
                "email",
                "password",
                "organization",
                "invite_token"
            ],
            "required_body": [],
            "body_defaults": {
                "mode": "signup"
            },
            "scope": None,
            "description": "Create a Tempera account (or accept an invite) and receive an account-session token pair."
        },
        {
            "id": "login",
            "method": "POST",
            "path": "/sessions",
            "auth": "none",
            "path_params": [],
            "query": [],
            "body": [
                "email",
                "password"
            ],
            "required_body": [],
            "body_defaults": {
                "mode": "login"
            },
            "scope": None,
            "description": "Log in with email and password and receive an account-session token pair."
        },
        {
            "id": "me",
            "method": "GET",
            "path": "/me",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the authenticated user's identity, active workspace, and roles."
        },
        {
            "id": "select_workspace",
            "method": "POST",
            "path": "/workspace/select",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [
                "org_id",
                "project_id",
                "environment_id"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Switch the active workspace and receive a token pair scoped to it."
        },
        {
            "id": "list_orgs",
            "method": "GET",
            "path": "/orgs",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List the organizations the authenticated user belongs to."
        },
        {
            "id": "create_org",
            "method": "POST",
            "path": "/orgs",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [
                "name"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Create an organization; the caller becomes its owner."
        },
        {
            "id": "list_projects",
            "method": "GET",
            "path": "/projects",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List projects across every organization the user belongs to."
        },
        {
            "id": "create_project",
            "method": "POST",
            "path": "/projects",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [
                "org_id",
                "name"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Create a project in an organization (requires an org admin role)."
        },
        {
            "id": "list_environments",
            "method": "GET",
            "path": "/environments",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List environments across every project the user can access."
        },
        {
            "id": "create_environment",
            "method": "POST",
            "path": "/environments",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [
                "project_id",
                "name"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Create an environment in a project (requires an org admin role)."
        },
        {
            "id": "list_team_members",
            "method": "GET",
            "path": "/team/members",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List team members of the active organization."
        },
        {
            "id": "update_team_member",
            "method": "PATCH",
            "path": "/team/members/{member_id}",
            "auth": "account",
            "path_params": [
                "member_id"
            ],
            "query": [],
            "body": [
                "role"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Change a team member's role (requires an org admin role; at least one owner must remain)."
        },
        {
            "id": "remove_team_member",
            "method": "DELETE",
            "path": "/team/members/{member_id}",
            "auth": "account",
            "path_params": [
                "member_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Remove a team member from the active organization (idempotent)."
        },
        {
            "id": "list_invites",
            "method": "GET",
            "path": "/invites",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List invites for the active organization, newest first."
        },
        {
            "id": "create_invite",
            "method": "POST",
            "path": "/invites",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [
                "email",
                "role"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Invite a user to the active organization; the accept URL is returned once."
        },
        {
            "id": "cancel_invite",
            "method": "DELETE",
            "path": "/invites/{invite_id}",
            "auth": "account",
            "path_params": [
                "invite_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Cancel a pending invite (idempotent)."
        },
        {
            "id": "list_api_keys",
            "method": "GET",
            "path": "/api-keys",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List API keys in the active workspace; secrets are never returned."
        },
        {
            "id": "create_api_key",
            "method": "POST",
            "path": "/api-keys",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [
                "scopes",
                "audience",
                "org_id",
                "project_id",
                "environment_id"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Mint a workspace API key (tp_...); the secret is returned exactly once. The workspace ids must match the token's workspace."
        },
        {
            "id": "rotate_api_key",
            "method": "POST",
            "path": "/api-keys/{api_key_id}/rotate",
            "auth": "account",
            "path_params": [
                "api_key_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Rotate an API key's secret; the new secret is returned exactly once."
        },
        {
            "id": "revoke_api_key",
            "method": "DELETE",
            "path": "/api-keys/{api_key_id}",
            "auth": "account",
            "path_params": [
                "api_key_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Revoke an API key (idempotent)."
        },
        {
            "id": "list_grants",
            "method": "GET",
            "path": "/oauth/grants",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List the OAuth grants the user has approved in the active workspace."
        },
        {
            "id": "revoke_grant",
            "method": "DELETE",
            "path": "/oauth/grants/{grant_id}",
            "auth": "account",
            "path_params": [
                "grant_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Revoke an OAuth grant and every refresh token issued under it."
        },
        {
            "id": "list_sessions",
            "method": "GET",
            "path": "/sessions",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List the user's active account sessions."
        },
        {
            "id": "revoke_session",
            "method": "DELETE",
            "path": "/sessions/{session_id}",
            "auth": "account",
            "path_params": [
                "session_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Revoke an account session and its tokens immediately (idempotent)."
        },
        {
            "id": "list_connectors",
            "method": "GET",
            "path": "/connectors",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List the connector catalog (MCP clients, editors, and API surfaces)."
        },
        {
            "id": "get_connector_status",
            "method": "GET",
            "path": "/connectors/{connector_id}/status",
            "auth": "account",
            "path_params": [
                "connector_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch one connector's connection status for the active workspace."
        },
        {
            "id": "list_products",
            "method": "GET",
            "path": "/products",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List the product catalog with default scopes and setup paths."
        },
        {
            "id": "get_product_status",
            "method": "GET",
            "path": "/products/{product_id}/status",
            "auth": "account",
            "path_params": [
                "product_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch one product's activation status, entitlements, signals, and usage meters."
        },
        {
            "id": "get_model_catalog",
            "method": "GET",
            "path": "/model-catalog",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "model:read",
            "description": "List the entitled Tempera Code model catalog; requires a tempera-code bearer with model:read and the model-gateway entitlement."
        },
        {
            "id": "get_billing_status",
            "method": "GET",
            "path": "/billing/status",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the organization's plan, subscription, usage meters, entitlements, invoices, and pricing (requires a billing role)."
        },
        {
            "id": "create_billing_checkout",
            "method": "GET",
            "path": "/billing/checkout",
            "auth": "account",
            "path_params": [],
            "query": [
                "rail",
                "plan_id",
                "billing_interval",
                "currency",
                "network"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Create a checkout handoff URL for a plan on the chosen payment rail (requires a billing role)."
        },
        {
            "id": "get_billing_portal",
            "method": "GET",
            "path": "/billing/portal",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the billing-portal URL for the organization (requires a billing role)."
        },
        {
            "id": "record_usage",
            "method": "POST",
            "path": "/usage/events",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [
                "metric",
                "quantity",
                "org_id",
                "project_id",
                "environment_id"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Record a usage event against a metered plan limit; requires a token carrying the meter's product scope and returns the updated meter."
        },
        {
            "id": "list_audit_log",
            "method": "GET",
            "path": "/audit-log",
            "auth": "account",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List recent audit-log events for the user and active organization (up to 50, newest first)."
        },
        {
            "id": "introspect_token",
            "method": "POST",
            "path": "/oauth/introspect",
            "auth": "introspectionSecret",
            "path_params": [],
            "query": [],
            "body": [
                "token"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Introspect a token or tp_ API key server-side; requires the introspection secret and returns {active: False} for anything invalid."
        }
    ],
    "palette": [
        {
            "id": "health",
            "method": "GET",
            "path": "/health",
            "auth": "none",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check palette API liveness; returns {ok: True}."
        },
        {
            "id": "list_traces",
            "method": "GET",
            "path": "/v1/traces/{tenant_id}",
            "auth": "product",
            "path_params": [
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
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:read",
            "description": "List trace summaries for a tenant with filters and cursor pagination."
        },
        {
            "id": "get_trace",
            "method": "GET",
            "path": "/v1/traces/{tenant_id}/{trace_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "trace_id"
            ],
            "query": [
                "unmask",
                "reason"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:read",
            "description": "Fetch one full trace with all canonical spans; unmasking PII requires the pii:unmask scope and a reason."
        },
        {
            "id": "get_span",
            "method": "GET",
            "path": "/v1/spans/{tenant_id}/{trace_id}/{span_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "trace_id",
                "span_id"
            ],
            "query": [
                "unmask",
                "reason"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:read",
            "description": "Fetch one canonical span by trace and span id."
        },
        {
            "id": "get_span_io",
            "method": "GET",
            "path": "/v1/spans/{tenant_id}/{trace_id}/{span_id}/io",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "trace_id",
                "span_id"
            ],
            "query": [
                "unmask",
                "reason"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:read",
            "description": "Fetch a span's recorded input and output values."
        },
        {
            "id": "search_spans",
            "method": "GET",
            "path": "/v1/search/{tenant_id}/spans",
            "auth": "product",
            "path_params": [
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
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:read",
            "description": "Search spans by text query and facet filters."
        },
        {
            "id": "ingest_span",
            "method": "POST",
            "path": "/v1/traces/native",
            "auth": "product",
            "path_params": [],
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
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:write",
            "description": "Ingest one native span; idempotent when an idempotency key is supplied."
        },
        {
            "id": "import_source",
            "method": "POST",
            "path": "/v1/import/{tenant_id}/{project_id}/{environment_id}",
            "auth": "product",
            "path_params": [
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
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:write",
            "description": "Import spans from a named external source payload."
        },
        {
            "id": "archive_trace",
            "method": "POST",
            "path": "/v1/archive/{tenant_id}/{project_id}/{trace_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "trace_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:read",
            "description": "Archive a trace to Parquet and return the archive manifest."
        },
        {
            "id": "create_dataset",
            "method": "POST",
            "path": "/v1/datasets/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "query": [],
            "body": [
                "name"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Create a dataset for curating cases from traces."
        },
        {
            "id": "promote_trace_to_case",
            "method": "POST",
            "path": "/v1/datasets/{tenant_id}/{project_id}/{dataset_id}/cases/from-trace",
            "auth": "product",
            "path_params": [
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
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Promote a trace (or one span of it) into a dataset case."
        },
        {
            "id": "create_dataset_version",
            "method": "POST",
            "path": "/v1/datasets/{tenant_id}/{project_id}/{dataset_id}/versions",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "dataset_id"
            ],
            "query": [],
            "body": [
                "case_ids"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Snapshot a dataset into an immutable version for evals and experiments."
        },
        {
            "id": "create_api_key",
            "method": "POST",
            "path": "/v1/api-keys/{tenant_id}/{project_id}/{environment_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "environment_id"
            ],
            "query": [],
            "body": [
                "scopes"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": "admin",
            "description": "Mint a palette-scoped API key; the secret is returned exactly once."
        },
        {
            "id": "revoke_api_key",
            "method": "POST",
            "path": "/v1/api-keys/{tenant_id}/{project_id}/{environment_id}/{api_key_id}/revoke",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "environment_id",
                "api_key_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "admin",
            "description": "Revoke a palette API key."
        },
        {
            "id": "get_usage_summary",
            "method": "GET",
            "path": "/v1/usage/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
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
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check tempod liveness; returns {ok: True}."
        },
        {
            "id": "ready",
            "method": "GET",
            "path": "/ready",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check tempod readiness, including engine attachment, drain state, and session capacity."
        },
        {
            "id": "openapi",
            "method": "GET",
            "path": "/openapi.json",
            "auth": "none",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch tempod's OpenAPI document, generated at runtime for this host."
        },
        {
            "id": "list_sessions",
            "method": "GET",
            "path": "/sessions",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List browser sessions with their state and creation time."
        },
        {
            "id": "create_session",
            "method": "POST",
            "path": "/sessions",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [
                "url",
                "driverless"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Open a browser session at a URL; driverless sessions skip engine attachment."
        },
        {
            "id": "close_session",
            "method": "DELETE",
            "path": "/sessions/{session_id}",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Close a browser session and release its engine resources."
        },
        {
            "id": "observe",
            "method": "GET",
            "path": "/sessions/{session_id}/observe",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the session's compiled structured observation (ranked, stably-identified elements)."
        },
        {
            "id": "act_batch",
            "method": "POST",
            "path": "/sessions/{session_id}/act_batch",
            "auth": "product",
            "path_params": [
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
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Apply a batch of semantic actions with policy gating; returns the applied diff or a policy decision."
        },
        {
            "id": "screenshot",
            "method": "GET",
            "path": "/sessions/{session_id}/screenshot",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "query": [
                "set_of_marks"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Capture a PNG screenshot of the session, optionally annotated with set-of-marks."
        },
        {
            "id": "session_events",
            "method": "GET",
            "path": "/sessions/{session_id}/events",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "query": [
                "after_seq"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the session's event window after a sequence number."
        },
        {
            "id": "adopt_session",
            "method": "POST",
            "path": "/sessions/{session_id}/adopt",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Let a human surface take write ownership of the session and receive an adoption lease."
        },
        {
            "id": "handoff_session",
            "method": "POST",
            "path": "/sessions/{session_id}/handoff",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Return write ownership of the session to the agent plane."
        },
        {
            "id": "create_run",
            "method": "POST",
            "path": "/sessions/{session_id}/runs",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "query": [],
            "body": [
                "goal",
                "actions",
                "max_rounds",
                "token_budget"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Start an agent run against the session with a goal, action budget, and round limit."
        },
        {
            "id": "list_runs",
            "method": "GET",
            "path": "/runs",
            "auth": "product",
            "path_params": [],
            "query": [
                "session_id"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List agent runs, optionally filtered to one session."
        },
        {
            "id": "get_run",
            "method": "GET",
            "path": "/runs/{run_id}",
            "auth": "product",
            "path_params": [
                "run_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch one agent run with its state."
        },
        {
            "id": "cancel_run",
            "method": "POST",
            "path": "/runs/{run_id}/cancel",
            "auth": "product",
            "path_params": [
                "run_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Cancel an agent run."
        },
        {
            "id": "resume_run",
            "method": "POST",
            "path": "/runs/{run_id}/resume",
            "auth": "product",
            "path_params": [
                "run_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Resume an agent run after a human handoff completes."
        },
        {
            "id": "grant_confirmation",
            "method": "POST",
            "path": "/sessions/{session_id}/confirmations/{confirmation_id}",
            "auth": "product",
            "path_params": [
                "session_id",
                "confirmation_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Grant a pending policy confirmation and receive a single-use grant token."
        }
    ],
    "temperaCode": [
        {
            "id": "health",
            "method": "GET",
            "path": "/healthz",
            "auth": "none",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check Tempera Code gateway liveness."
        },
        {
            "id": "list_models",
            "method": "GET",
            "path": "/v1/models",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "model:read",
            "description": "List the entitled Tempera Code hosted model catalog."
        },
        {
            "id": "create_response",
            "method": "POST",
            "path": "/v1/responses",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [
                "model",
                "input",
                "instructions",
                "tools",
                "text"
            ],
            "required_body": [
                "model",
                "input"
            ],
            "body_defaults": {},
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
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check tempera-llm gateway liveness; returns {ok: True}."
        },
        {
            "id": "list_models",
            "method": "GET",
            "path": "/v1/models",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "model:read",
            "description": "List the configured model catalog the gateway can route to."
        },
        {
            "id": "create_chat_completion",
            "method": "POST",
            "path": "/v1/chat/completions",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [
                "model",
                "messages",
                "max_tokens",
                "temperature",
                "stream",
                "byok"
            ],
            "required_body": [
                "model",
                "messages"
            ],
            "body_defaults": {},
            "scope": "model:invoke",
            "description": "Create a non-streaming OpenAI-compatible chat completion through the tempera-llm gateway."
        },
        {
            "id": "create_response",
            "method": "POST",
            "path": "/v1/responses",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [
                "model",
                "input",
                "max_output_tokens",
                "byok"
            ],
            "required_body": [
                "model",
                "input"
            ],
            "body_defaults": {},
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
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check tempera-workflows engine liveness."
        },
        {
            "id": "list_node_types",
            "method": "GET",
            "path": "/v1/node-types",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:read",
            "description": "List the typed node catalog: native orchestration nodes plus the sdk.<product>.<operation> nodes generated from the SDK surface."
        },
        {
            "id": "list_workflows",
            "method": "GET",
            "path": "/v1/workflows",
            "auth": "product",
            "path_params": [],
            "query": [
                "limit"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:read",
            "description": "List stored workflow definitions, newest first."
        },
        {
            "id": "create_workflow",
            "method": "POST",
            "path": "/v1/workflows",
            "auth": "product",
            "path_params": [],
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
            "required_body": [
                "contractVersion",
                "id",
                "name",
                "nodes",
                "edges"
            ],
            "body_defaults": {},
            "scope": "workflow:write",
            "description": "Create a workflow definition (tempera.workflow/v1 bounded DAG of typed nodes); the definition is validated before it is stored."
        },
        {
            "id": "get_workflow",
            "method": "GET",
            "path": "/v1/workflows/{workflow_id}",
            "auth": "product",
            "path_params": [
                "workflow_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:read",
            "description": "Fetch one stored workflow definition."
        },
        {
            "id": "update_workflow",
            "method": "PUT",
            "path": "/v1/workflows/{workflow_id}",
            "auth": "product",
            "path_params": [
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
            "required_body": [
                "contractVersion",
                "id",
                "name",
                "nodes",
                "edges"
            ],
            "body_defaults": {},
            "scope": "workflow:write",
            "description": "Replace a stored workflow definition with a new validated revision."
        },
        {
            "id": "delete_workflow",
            "method": "DELETE",
            "path": "/v1/workflows/{workflow_id}",
            "auth": "product",
            "path_params": [
                "workflow_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:write",
            "description": "Delete a stored workflow definition."
        },
        {
            "id": "validate_workflow",
            "method": "POST",
            "path": "/v1/workflows:validate",
            "auth": "product",
            "path_params": [],
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
            "required_body": [
                "contractVersion",
                "id",
                "name",
                "nodes",
                "edges"
            ],
            "body_defaults": {},
            "scope": "workflow:write",
            "description": "Validate a workflow definition without storing it; returns the full diagnostic list."
        },
        {
            "id": "compose_workflow",
            "method": "POST",
            "path": "/v1/workflows/{workflow_id}:compose",
            "auth": "product",
            "path_params": [
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
            "required_body": [
                "prompt"
            ],
            "body_defaults": {},
            "scope": "workflow:write",
            "description": "Search the full SDK-backed node catalog or ask Tempera Code to propose a validated workflow draft without saving or running it."
        },
        {
            "id": "assist_json",
            "method": "POST",
            "path": "/v1/workflows:assistJson",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [
                "mode",
                "purpose",
                "expectedRoot",
                "context",
                "current",
                "prompt"
            ],
            "required_body": [
                "mode",
                "purpose",
                "expectedRoot"
            ],
            "body_defaults": {},
            "scope": "workflow:write",
            "description": "Generate or repair one JSON editor value and validate its requested root and purpose without saving a workflow or executing a node."
        },
        {
            "id": "create_run",
            "method": "POST",
            "path": "/v1/workflows/{workflow_id}/runs",
            "auth": "product",
            "path_params": [
                "workflow_id"
            ],
            "query": [],
            "body": [
                "input",
                "idempotencyKey"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:run",
            "description": "Start a run of a stored workflow with an optional input document and idempotency key."
        },
        {
            "id": "call_workflow",
            "method": "POST",
            "path": "/v1/workflows/{workflow_id}:call",
            "auth": "product",
            "path_params": [
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
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:run",
            "description": "Run a workflow to completion and return its output in a single call."
        },
        {
            "id": "list_runs",
            "method": "GET",
            "path": "/v1/runs",
            "auth": "product",
            "path_params": [],
            "query": [
                "workflowId",
                "limit"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:read",
            "description": "List workflow runs, optionally filtered to one workflow."
        },
        {
            "id": "get_run",
            "method": "GET",
            "path": "/v1/runs/{run_id}",
            "auth": "product",
            "path_params": [
                "run_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:read",
            "description": "Fetch one workflow run with its state, node results, and timings; the live SSE event stream at /v1/runs/{run_id}/events is passthrough-only."
        },
        {
            "id": "cancel_run",
            "method": "POST",
            "path": "/v1/runs/{run_id}:cancel",
            "auth": "product",
            "path_params": [
                "run_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
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
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check tempera-gym service liveness."
        },
        {
            "id": "list_environments",
            "method": "GET",
            "path": "/v1/environments",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List the gym pack's environment catalog, including implementation status and per-environment manifests."
        },
        {
            "id": "list_runs",
            "method": "GET",
            "path": "/v1/runs",
            "auth": "product",
            "path_params": [],
            "query": [
                "environment_id",
                "limit"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List persisted rollout run index records, newest first."
        },
        {
            "id": "get_run",
            "method": "GET",
            "path": "/v1/runs/{run}",
            "auth": "product",
            "path_params": [
                "run"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one persisted run's index record and verified trajectory-v1 envelope by run id or trajectory content hash."
        },
        {
            "id": "create_rollout",
            "method": "POST",
            "path": "/v1/rollouts",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [
                "environment_id",
                "policy",
                "seed",
                "max_steps",
                "model"
            ],
            "required_body": [
                "environment_id",
                "seed"
            ],
            "body_defaults": {},
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
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check sandbox-daemon liveness; returns status, version, and uptime."
        },
        {
            "id": "get_capabilities",
            "method": "GET",
            "path": "/v1/capabilities",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the sandbox capability matrix: lanes, engines, limits, and integrations."
        },
        {
            "id": "get_integration_contract",
            "method": "GET",
            "path": "/v1/integration",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the ecosystem integration contract this daemon implements."
        },
        {
            "id": "execute",
            "method": "POST",
            "path": "/v1/execute",
            "auth": "product",
            "path_params": [],
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
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Execute source synchronously in a sandbox lane and return the result with metrics."
        },
        {
            "id": "create_job",
            "method": "POST",
            "path": "/v1/jobs",
            "auth": "product",
            "path_params": [],
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
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Submit an asynchronous sandbox job; returns an operation handle to poll."
        },
        {
            "id": "get_job",
            "method": "GET",
            "path": "/v1/jobs/{job_id}",
            "auth": "product",
            "path_params": [
                "job_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch a sandbox job's status and result."
        },
        {
            "id": "cancel_job",
            "method": "DELETE",
            "path": "/v1/jobs/{job_id}",
            "auth": "product",
            "path_params": [
                "job_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Cancel a queued or running sandbox job (idempotent for already-cancelled jobs)."
        },
        {
            "id": "get_browser_profiles",
            "method": "GET",
            "path": "/v1/browser/profiles",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the browser sandbox profile levels and suppression modes this daemon offers."
        },
        {
            "id": "admit_browser_session",
            "method": "POST",
            "path": "/v1/browser/admit",
            "auth": "product",
            "path_params": [],
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
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Request admission for a browser session at a sandbox level and receive the guard plan."
        },
        {
            "id": "get_browser_adapter_contract",
            "method": "GET",
            "path": "/v1/browser/adapter/contract",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the browser adapter contract, required controls, and conformance profile."
        }
    ],
    "remi": [
        {
            "id": "livez",
            "method": "GET",
            "path": "/livez",
            "auth": "none",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check memory-server liveness."
        },
        {
            "id": "readyz",
            "method": "GET",
            "path": "/readyz",
            "auth": "none",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check memory-server readiness, including database health."
        },
        {
            "id": "health",
            "method": "GET",
            "path": "/v1/health",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch deep store health: schema version, integrity checks, and graph consistency."
        },
        {
            "id": "get_stats",
            "method": "GET",
            "path": "/v1/stats",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch memory-store statistics: ledger events, nodes, and token counts by kind."
        },
        {
            "id": "get_metrics",
            "method": "GET",
            "path": "/v1/metrics",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch service metrics as JSON, including per-route counters and query-tier latencies."
        },
        {
            "id": "get_prometheus_metrics",
            "method": "GET",
            "path": "/v1/metrics/prometheus",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch service metrics in Prometheus text exposition format for scrape-based monitoring."
        },
        {
            "id": "list_audit",
            "method": "GET",
            "path": "/v1/audit",
            "auth": "product",
            "path_params": [],
            "query": [
                "limit"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List recent service audit events (default 100, maximum 500)."
        },
        {
            "id": "remember",
            "method": "POST",
            "path": "/v1/remember",
            "auth": "product",
            "path_params": [],
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
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Write one memory into the ledger and, by default, project it into the memory graph immediately."
        },
        {
            "id": "project",
            "method": "POST",
            "path": "/v1/project",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [
                "limit"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Project pending ledger events into the memory graph and return the projection report."
        },
        {
            "id": "manage",
            "method": "POST",
            "path": "/v1/manage",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [
                "limit"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Run memory management over pending ledger events (same engine pass as project, tracked separately)."
        },
        {
            "id": "query",
            "method": "POST",
            "path": "/v1/query",
            "auth": "product",
            "path_params": [],
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
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Answer a question from memory with evidence, citations, contradictions, and staleness signals."
        },
        {
            "id": "maintenance",
            "method": "POST",
            "path": "/v1/maintenance",
            "auth": "product",
            "path_params": [],
            "query": [],
            "body": [
                "vacuum",
                "repair_orphans",
                "prune_audit_before_unix_ms",
                "retain_latest_audit_events"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Run store maintenance: optimize, checkpoint, and optionally vacuum, repair orphans, and prune audit history."
        }
    ],
    "dataEngine": [
        {
            "id": "health",
            "method": "GET",
            "path": "/v1/health",
            "auth": "none",
            "path_params": [],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check data-engine liveness; returns the service status."
        },
        {
            "id": "admit_training_release",
            "method": "POST",
            "path": "/v1/projects/{project_id}/training-releases:admit",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [],
            "body": [
                "training_product_id",
                "heldout_product_id",
                "idempotency_key"
            ],
            "required_body": [
                "training_product_id",
                "heldout_product_id",
                "idempotency_key"
            ],
            "body_defaults": {},
            "scope": "training:publish",
            "description": "Admit exact training and heldout product generations after revalidating integrity, review consent, and leakage constraints."
        },
        {
            "id": "get_training_release",
            "method": "GET",
            "path": "/v1/projects/{project_id}/training-releases/{release_id}",
            "auth": "product",
            "path_params": [
                "project_id",
                "release_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "training:publish",
            "description": "Revalidate and fetch one training release, including any durable stale state."
        },
        {
            "id": "create_evidence_record",
            "method": "POST",
            "path": "/v1/projects/{project_id}/evidenceRecords",
            "auth": "product",
            "path_params": [
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
            "required_body": [
                "schema_version",
                "domain",
                "evidence_type",
                "payload_schema",
                "payload",
                "source_artifact_refs",
                "verification_state"
            ],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Create an immutable shared evidence record by canonical content hash."
        },
        {
            "id": "list_evidence_records",
            "method": "GET",
            "path": "/v1/projects/{project_id}/evidenceRecords",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [
                "page_size",
                "page_token",
                "domain"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List immutable shared evidence records with bounded cursor pagination."
        },
        {
            "id": "get_evidence_record",
            "method": "GET",
            "path": "/v1/projects/{project_id}/evidenceRecords/{evidence_record_id}",
            "auth": "product",
            "path_params": [
                "project_id",
                "evidence_record_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one immutable shared evidence record by its platform digest."
        },
        {
            "id": "create_episode",
            "method": "POST",
            "path": "/v1/projects/{project_id}/episodes",
            "auth": "product",
            "path_params": [
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
            "required_body": [
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
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Create an immutable shared episode by canonical content hash."
        },
        {
            "id": "list_episodes",
            "method": "GET",
            "path": "/v1/projects/{project_id}/episodes",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [
                "page_size",
                "page_token",
                "domain"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List immutable shared episodes with bounded cursor pagination."
        },
        {
            "id": "get_episode",
            "method": "GET",
            "path": "/v1/projects/{project_id}/episodes/{episode_id}",
            "auth": "product",
            "path_params": [
                "project_id",
                "episode_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one immutable shared episode by its platform digest."
        },
        {
            "id": "query_research_retrieval",
            "method": "POST",
            "path": "/v1/projects/{project_id}/researchRetrieval:query",
            "auth": "product",
            "path_params": [
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
            "required_body": [
                "contractVersion",
                "requestId",
                "obligation",
                "limit"
            ],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Retrieve deterministic candidates for one exact canonical typed research obligation."
        },
        {
            "id": "create_research_catalog_entry",
            "method": "POST",
            "path": "/v1/projects/{project_id}/researchCatalogEntries",
            "auth": "product",
            "path_params": [
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
            "required_body": [
                "kind",
                "version",
                "obligationHash",
                "capabilityRoute",
                "provenance"
            ],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Create an immutable executable research catalog entry by canonical content hash."
        },
        {
            "id": "list_research_catalog_entries",
            "method": "GET",
            "path": "/v1/projects/{project_id}/researchCatalogEntries",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [
                "page_size",
                "page_token"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List immutable executable research catalog entries with bounded pagination."
        },
        {
            "id": "get_research_catalog_entry",
            "method": "GET",
            "path": "/v1/projects/{project_id}/researchCatalogEntries/{entry_id}",
            "auth": "product",
            "path_params": [
                "project_id",
                "entry_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one immutable executable research catalog entry by content hash."
        },
        {
            "id": "list_connectors",
            "method": "GET",
            "path": "/v1/projects/{project_id}/connectors",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [
                "page_size",
                "page_token"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List registered source connectors for a project."
        },
        {
            "id": "list_use_cases",
            "method": "GET",
            "path": "/v1/projects/{project_id}/use-cases",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [
                "page_size",
                "page_token"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List the MVP use-case templates (data products and pipeline templates) for a project."
        },
        {
            "id": "get_use_case",
            "method": "GET",
            "path": "/v1/projects/{project_id}/use-cases/{use_case_id}",
            "auth": "product",
            "path_params": [
                "project_id",
                "use_case_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one MVP use-case template with its rubric, modalities, skill tags, and target accuracy."
        },
        {
            "id": "ingest_artifact",
            "method": "POST",
            "path": "/v1/projects/{project_id}/artifacts:ingest",
            "auth": "product",
            "path_params": [
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
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Ingest one artifact deterministically into the project; returns an async operation handle."
        },
        {
            "id": "ingest_web",
            "method": "POST",
            "path": "/v1/projects/{project_id}/web:ingest",
            "auth": "product",
            "path_params": [
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
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Fetch, parse, and ingest one public HTTP(S) page as a web artifact; returns an async operation handle."
        },
        {
            "id": "run_use_case",
            "method": "POST",
            "path": "/v1/projects/{project_id}/pipelines:run-use-case",
            "auth": "product",
            "path_params": [
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
            "required_body": [],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Run a complete MVP use-case pipeline end to end; verifier selects the configured verification backend."
        },
        {
            "id": "create_campaign",
            "method": "POST",
            "path": "/v1/projects/{project_id}/campaigns",
            "auth": "product",
            "path_params": [
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
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Create a data campaign with a rubric, budget, target accuracy, and skill tags."
        },
        {
            "id": "list_campaigns",
            "method": "GET",
            "path": "/v1/projects/{project_id}/campaigns",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [
                "page_size",
                "page_token"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List a project's data campaigns with pagination."
        },
        {
            "id": "transition_campaign",
            "method": "POST",
            "path": "/v1/projects/{project_id}/campaigns/{campaign_id}:transition",
            "auth": "product",
            "path_params": [
                "project_id",
                "campaign_id"
            ],
            "query": [],
            "body": [
                "target_status",
                "idempotency_key"
            ],
            "required_body": [
                "target_status",
                "idempotency_key"
            ],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Pause, resume, or permanently close campaign job admission; returns an immutable receipt for the committed lifecycle transition."
        },
        {
            "id": "list_artifacts",
            "method": "GET",
            "path": "/v1/projects/{project_id}/artifacts",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [
                "page_size",
                "page_token",
                "view"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List a project's artifacts with cursor pagination, expanded to the requested view (BASIC or FULL)."
        },
        {
            "id": "get_artifact",
            "method": "GET",
            "path": "/v1/projects/{project_id}/artifacts/{artifact_id}",
            "auth": "product",
            "path_params": [
                "project_id",
                "artifact_id"
            ],
            "query": [
                "view"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one artifact, expanded to the requested view (BASIC or FULL)."
        },
        {
            "id": "list_artifact_labels",
            "method": "GET",
            "path": "/v1/projects/{project_id}/artifacts/{artifact_id}/labels",
            "auth": "product",
            "path_params": [
                "project_id",
                "artifact_id"
            ],
            "query": [
                "page_size",
                "page_token"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List the labels attached to one artifact."
        },
        {
            "id": "profile_dataset",
            "method": "POST",
            "path": "/v1/projects/{project_id}/datasets:profile",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [],
            "body": [
                "artifact_ids",
                "artifact_type"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Profile dataset quality before export, including duplicates, label coverage, and distributions."
        },
        {
            "id": "create_job",
            "method": "POST",
            "path": "/v1/projects/{project_id}/jobs",
            "auth": "product",
            "path_params": [
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
            "required_body": [],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Create an asynchronous labeling job over a set of artifacts; returns an operation handle to poll."
        },
        {
            "id": "get_job",
            "method": "GET",
            "path": "/v1/projects/{project_id}/jobs/{job_id}",
            "auth": "product",
            "path_params": [
                "project_id",
                "job_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one labeling job with its state and progress."
        },
        {
            "id": "get_job_results",
            "method": "GET",
            "path": "/v1/projects/{project_id}/jobs/{job_id}/results",
            "auth": "product",
            "path_params": [
                "project_id",
                "job_id"
            ],
            "query": [
                "page_size",
                "page_token"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List the deterministic label results a job produced."
        },
        {
            "id": "list_expert_tasks",
            "method": "GET",
            "path": "/v1/projects/{project_id}/expert-tasks",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [
                "page_size",
                "page_token",
                "status",
                "campaign_name"
            ],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List human residual review tasks, optionally filtered by status and campaign."
        },
        {
            "id": "resolve_expert_task",
            "method": "POST",
            "path": "/v1/projects/{project_id}/expert-tasks/{expert_task_id}:resolve",
            "auth": "product",
            "path_params": [
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
            "required_body": [
                "label",
                "idempotency_key",
                "review_context"
            ],
            "body_defaults": {},
            "scope": "review:resolve",
            "description": "Resolve, abstain, flag, or adjudicate one human residual with an idempotent normalized decision."
        },
        {
            "id": "get_metrics",
            "method": "GET",
            "path": "/v1/projects/{project_id}/metrics",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch data-engine usage and quality metrics for a project."
        },
        {
            "id": "get_label_quality",
            "method": "GET",
            "path": "/v1/projects/{project_id}/label-quality",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch the project label-quality report and unresolved expert backlog."
        },
        {
            "id": "get_ecosystem_readiness",
            "method": "GET",
            "path": "/v1/projects/{project_id}/ecosystem/readiness",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch public-site and ecosystem readiness signals for a project."
        },
        {
            "id": "emit_eval",
            "method": "POST",
            "path": "/v1/projects/{project_id}/products:emit-eval",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [],
            "body": [
                "artifact_ids",
                "include_provenance",
                "license",
                "filters"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Emit an eval dataset bundle from verified artifacts; returns an async operation handle."
        },
        {
            "id": "derive_bundle",
            "method": "POST",
            "path": "/v1/projects/{project_id}/products/{product_id}:derive",
            "auth": "product",
            "path_params": [
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
            "required_body": [],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Derive a deterministic post-training bundle from a ready product."
        },
        {
            "id": "get_product",
            "method": "GET",
            "path": "/v1/projects/{project_id}/products/{product_id}",
            "auth": "product",
            "path_params": [
                "project_id",
                "product_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one emitted product bundle with its status and manifest URL."
        },
        {
            "id": "validate_product",
            "method": "POST",
            "path": "/v1/projects/{project_id}/products/{product_id}:validate",
            "auth": "product",
            "path_params": [
                "project_id",
                "product_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Validate an emitted product bundle's referential integrity and hygiene."
        },
        {
            "id": "check_product_leakage",
            "method": "POST",
            "path": "/v1/projects/{project_id}/products:check-leakage",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [],
            "body": [
                "product_ids"
            ],
            "required_body": [
                "product_ids"
            ],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Check raw-hash leakage between exactly two product bundles."
        },
        {
            "id": "get_product_manifest",
            "method": "GET",
            "path": "/v1/projects/{project_id}/products/{product_id}/manifest",
            "auth": "product",
            "path_params": [
                "project_id",
                "product_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch an integrity-checked, bounded manifest for an emitted eval product."
        },
        {
            "id": "extract_source",
            "method": "POST",
            "path": "/v1/projects/{project_id}/sources:extract",
            "auth": "product",
            "path_params": [
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
            "required_body": [
                "connector"
            ],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Extract bounded objects or records from a configured source connector."
        },
        {
            "id": "create_tool",
            "method": "POST",
            "path": "/v1/projects/{project_id}/tools",
            "auth": "product",
            "path_params": [
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
            "required_body": [
                "name",
                "description",
                "kind",
                "implementation"
            ],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Create or version-bump a stored custom tool."
        },
        {
            "id": "list_tools",
            "method": "GET",
            "path": "/v1/projects/{project_id}/tools",
            "auth": "product",
            "path_params": [
                "project_id"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List stored custom tools and their usage statistics."
        },
        {
            "id": "get_tool",
            "method": "GET",
            "path": "/v1/projects/{project_id}/tools/{tool_name}",
            "auth": "product",
            "path_params": [
                "project_id",
                "tool_name"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one stored custom tool and its usage statistics."
        },
        {
            "id": "delete_tool",
            "method": "DELETE",
            "path": "/v1/projects/{project_id}/tools/{tool_name}",
            "auth": "product",
            "path_params": [
                "project_id",
                "tool_name"
            ],
            "query": [],
            "body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Delete a stored custom tool and every retained version."
        },
        {
            "id": "invoke_tool",
            "method": "POST",
            "path": "/v1/projects/{project_id}/tools/{tool_name}:invoke",
            "auth": "product",
            "path_params": [
                "project_id",
                "tool_name"
            ],
            "query": [],
            "body": [
                "arguments"
            ],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Invoke a stored custom tool through its configured execution boundary."
        }
    ]
}

MCP_GATEWAY = {
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
            "id": "list_tools",
            "rpc": "tools/list",
            "description": "List every tool the gateway offers: builtins plus namespaced product tools."
        },
        {
            "id": "call_tool",
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
