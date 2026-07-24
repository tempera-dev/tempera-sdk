"""GENERATED FROM surface.json by scripts/gen-sdk-surface.py -- DO NOT EDIT BY HAND.

The SDK surface tables: products, audiences, scopes, environments, the
error contract, and every typed operation, shared verbatim with the
TypeScript and Rust packages.
"""

SURFACE_VERSION = 4

AUDIENCES = ('palette', 'tempo', 'cradle', 'remi', 'human-data', 'data-engine', 'tempera-mcp', 'tempera-code', 'tempera-llm', 'tempera-workflows', 'tempera-gym')
DEFAULT_AUDIENCE = 'palette'
SCOPES = ('mcp:invoke', 'memory:read', 'memory:write', 'memory:manage', 'trace:read', 'trace:write', 'dataset:read', 'dataset:write', 'eval:run', 'training:publish', 'review:gold:manage', 'review:resolve', 'workflow:read', 'workflow:write', 'workflow:run', 'model:read', 'model:invoke', 'pii:unmask', 'admin')

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
            "upstream_operation_id": "getHealth",
            "method": "GET",
            "path": "/healthz",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check control-plane liveness; returns {ok: True}."
        },
        {
            "id": "get_readiness",
            "upstream_operation_id": "getReadiness",
            "method": "GET",
            "path": "/readyz",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Readiness probe for durable control-plane storage."
        },
        {
            "id": "me",
            "upstream_operation_id": "getMe",
            "method": "GET",
            "path": "/v1/me",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the authenticated user's identity, active workspace, and roles."
        },
        {
            "id": "list_orgs",
            "upstream_operation_id": "listOrganizations",
            "method": "GET",
            "path": "/v1/orgs",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List the organizations the authenticated user belongs to."
        },
        {
            "id": "create_org",
            "upstream_operation_id": "createOrganization",
            "method": "POST",
            "path": "/v1/orgs",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "name"
            ],
            "forbidden_body": [],
            "required_body": [
                "name"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Create an organization; the caller becomes its owner."
        },
        {
            "id": "list_sessions",
            "upstream_operation_id": "listAccountSessions",
            "method": "GET",
            "path": "/v1/sessions",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List the user's active account sessions."
        },
        {
            "id": "create_hosted_session",
            "upstream_operation_id": "createHostedSession",
            "method": "POST",
            "path": "/v1/sessions",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "mode",
                "email",
                "password",
                "organization",
                "inviteToken"
            ],
            "forbidden_body": [],
            "required_body": [
                "email",
                "password"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Create a first-party hosted account session from email/password login or signup."
        },
        {
            "id": "revoke_session",
            "upstream_operation_id": "revokeAccountSession",
            "method": "DELETE",
            "path": "/v1/sessions/{id}",
            "auth": "account",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Revoke an account session and its tokens immediately (idempotent)."
        },
        {
            "id": "select_workspace",
            "upstream_operation_id": "selectWorkspace",
            "method": "POST",
            "path": "/v1/workspace/select",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "orgId",
                "projectId",
                "environmentId"
            ],
            "forbidden_body": [],
            "required_body": [
                "orgId",
                "projectId",
                "environmentId"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Switch the active workspace and receive a token pair scoped to it."
        },
        {
            "id": "list_team_members",
            "upstream_operation_id": "listTeamMembers",
            "method": "GET",
            "path": "/v1/team/members",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List team members of the active organization."
        },
        {
            "id": "update_team_member",
            "upstream_operation_id": "updateTeamMember",
            "method": "PATCH",
            "path": "/v1/team/members/{id}",
            "auth": "account",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [
                "updateMask"
            ],
            "body": [
                "role"
            ],
            "forbidden_body": [],
            "required_body": [
                "role"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Change a team member's role (requires an org admin role; at least one owner must remain)."
        },
        {
            "id": "remove_team_member",
            "upstream_operation_id": "removeTeamMember",
            "method": "DELETE",
            "path": "/v1/team/members/{id}",
            "auth": "account",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Remove a team member from the active organization (idempotent)."
        },
        {
            "id": "list_invites",
            "upstream_operation_id": "listInvites",
            "method": "GET",
            "path": "/v1/invites",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List invites for the active organization, newest first."
        },
        {
            "id": "create_invite",
            "upstream_operation_id": "createInvite",
            "method": "POST",
            "path": "/v1/invites",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "email",
                "role"
            ],
            "forbidden_body": [],
            "required_body": [
                "email",
                "role"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Invite a user to the active organization; the accept URL is returned once."
        },
        {
            "id": "cancel_invite",
            "upstream_operation_id": "cancelInvite",
            "method": "DELETE",
            "path": "/v1/invites/{id}",
            "auth": "account",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Cancel a pending invite (idempotent)."
        },
        {
            "id": "list_projects",
            "upstream_operation_id": "listProjects",
            "method": "GET",
            "path": "/v1/projects",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List projects across every organization the user belongs to."
        },
        {
            "id": "create_project",
            "upstream_operation_id": "createProject",
            "method": "POST",
            "path": "/v1/projects",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "orgId",
                "name"
            ],
            "forbidden_body": [],
            "required_body": [
                "orgId",
                "name"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Create a project in an organization (requires an org admin role)."
        },
        {
            "id": "list_environments",
            "upstream_operation_id": "listEnvironments",
            "method": "GET",
            "path": "/v1/environments",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List environments across every project the user can access."
        },
        {
            "id": "create_environment",
            "upstream_operation_id": "createEnvironment",
            "method": "POST",
            "path": "/v1/environments",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "projectId",
                "name"
            ],
            "forbidden_body": [],
            "required_body": [
                "projectId",
                "name"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Create an environment in a project (requires an org admin role)."
        },
        {
            "id": "list_api_keys",
            "upstream_operation_id": "listApiKeys",
            "method": "GET",
            "path": "/v1/api-keys",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List API keys in the active workspace; secrets are never returned."
        },
        {
            "id": "create_api_key",
            "upstream_operation_id": "createApiKey",
            "method": "POST",
            "path": "/v1/api-keys",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "orgId",
                "projectId",
                "environmentId",
                "scopes"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Mint a workspace API key (tp_...); the secret is returned exactly once. The workspace ids must match the token's workspace."
        },
        {
            "id": "revoke_api_key",
            "upstream_operation_id": "revokeApiKey",
            "method": "DELETE",
            "path": "/v1/api-keys/{id}",
            "auth": "account",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Revoke an API key (idempotent)."
        },
        {
            "id": "rotate_api_key",
            "upstream_operation_id": "rotateApiKey",
            "method": "POST",
            "path": "/v1/api-keys/{id}/rotate",
            "auth": "account",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Rotate an API key's secret; the new secret is returned exactly once."
        },
        {
            "id": "provider_connections_list",
            "upstream_operation_id": "providerConnections.list",
            "method": "GET",
            "path": "/v1/provider-connections",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List provider connection metadata using a first-party account session. Secret references and values are never returned."
        },
        {
            "id": "provider_connections_create",
            "upstream_operation_id": "providerConnections.create",
            "method": "POST",
            "path": "/v1/provider-connections",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "orgId",
                "projectId",
                "environmentId",
                "provider",
                "name",
                "secretRef"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Create a tenant-scoped provider connection using only an external secret reference."
        },
        {
            "id": "provider_connections_revoke",
            "upstream_operation_id": "providerConnections.revoke",
            "method": "DELETE",
            "path": "/v1/provider-connections/{id}",
            "auth": "account",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Revoke a provider connection immediately. Revoking an unknown id is a no-op."
        },
        {
            "id": "provider_connections_rotate",
            "upstream_operation_id": "providerConnections.rotate",
            "method": "POST",
            "path": "/v1/provider-connections/{id}:rotate",
            "auth": "account",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "secretRef",
                "allowedModels"
            ],
            "forbidden_body": [],
            "required_body": [
                "secretRef"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Replace a connection secret reference and increment its revision without exposing the reference."
        },
        {
            "id": "provider_connections_resolve",
            "upstream_operation_id": "providerConnections.resolve",
            "method": "POST",
            "path": "/v1/provider-connections/{id}:resolve",
            "auth": "account",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "orgId",
                "projectId",
                "environmentId",
                "usageDelegation"
            ],
            "forbidden_body": [],
            "required_body": [
                "orgId",
                "projectId",
                "environmentId",
                "usageDelegation"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Resolve connection runtime metadata for a tenant-bound tempera-llm service credential."
        },
        {
            "id": "list_audit_log",
            "upstream_operation_id": "listAuditLog",
            "method": "GET",
            "path": "/v1/audit-log",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List recent audit-log events for the user and active organization (up to 50, newest first)."
        },
        {
            "id": "list_connectors",
            "upstream_operation_id": "listConnectors",
            "method": "GET",
            "path": "/v1/connectors",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List the connector catalog (MCP clients, editors, and API surfaces)."
        },
        {
            "id": "get_connector_status",
            "upstream_operation_id": "getConnectorStatus",
            "method": "GET",
            "path": "/v1/connectors/{id}/status",
            "auth": "account",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch one connector's connection status for the active workspace."
        },
        {
            "id": "list_products",
            "upstream_operation_id": "listProducts",
            "method": "GET",
            "path": "/v1/products",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List the product catalog with default scopes and setup paths."
        },
        {
            "id": "get_product_status",
            "upstream_operation_id": "getProductStatus",
            "method": "GET",
            "path": "/v1/products/{id}/status",
            "auth": "account",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch one product's activation status, entitlements, signals, and usage meters."
        },
        {
            "id": "get_billing_status",
            "upstream_operation_id": "getBillingStatus",
            "method": "GET",
            "path": "/v1/billing/status",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the organization's plan, subscription, usage meters, entitlements, invoices, and pricing (requires a billing role)."
        },
        {
            "id": "create_billing_checkout",
            "upstream_operation_id": "createBillingCheckout",
            "method": "GET",
            "path": "/v1/billing/checkout",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "rail",
                "plan",
                "planId",
                "interval",
                "currency",
                "network"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Create a checkout handoff URL for a plan on the chosen payment rail (requires a billing role)."
        },
        {
            "id": "get_billing_portal",
            "upstream_operation_id": "createBillingPortal",
            "method": "GET",
            "path": "/v1/billing/portal",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the billing-portal URL for the organization (requires a billing role)."
        },
        {
            "id": "get_billing_credits",
            "upstream_operation_id": "getBillingCredits",
            "method": "GET",
            "path": "/v1/billing/credits",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Return the org credit wallet balance, grant, overage, and recent ledger for owner, admin, or billing users. Internal cost/margin fields are redacted from the ledger for non-staff callers and returned in full only to platform staff."
        },
        {
            "id": "get_model_catalog",
            "upstream_operation_id": "getModelCatalog",
            "method": "GET",
            "path": "/v1/model-catalog",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "model:read",
            "description": "List the entitled Tempera Code model catalog; requires a tempera-code bearer with model:read and the model-gateway entitlement."
        },
        {
            "id": "record_usage",
            "upstream_operation_id": "recordUsageEvent",
            "method": "POST",
            "path": "/v1/usage/events",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "orgId",
                "projectId",
                "environmentId",
                "metric"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Record a usage event against a metered plan limit; requires a token carrying the meter's product scope and returns the updated meter."
        },
        {
            "id": "usage_reservations_create",
            "upstream_operation_id": "usageReservations.create",
            "method": "POST",
            "path": "/v1/usage/reservations",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
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
            "body_defaults": {},
            "scope": None,
            "description": "Atomically reserve the maximum model cost before starting a provider request."
        },
        {
            "id": "usage_reservations_commit",
            "upstream_operation_id": "usageReservations.commit",
            "method": "POST",
            "path": "/v1/usage/reservations/{reservationId}:commit",
            "auth": "account",
            "path_params": [
                "reservationId"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "orgId",
                "projectId",
                "environmentId",
                "configId",
                "cost"
            ],
            "forbidden_body": [],
            "required_body": [
                "orgId",
                "projectId",
                "environmentId",
                "configId",
                "cost"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Commit exact provider usage against an admitted reservation and release unused capacity."
        },
        {
            "id": "usage_reservations_release",
            "upstream_operation_id": "usageReservations.release",
            "method": "POST",
            "path": "/v1/usage/reservations/{reservationId}:release",
            "auth": "account",
            "path_params": [
                "reservationId"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "orgId",
                "projectId",
                "environmentId"
            ],
            "forbidden_body": [],
            "required_body": [
                "orgId",
                "projectId",
                "environmentId"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Release unused capacity after provider failure or cancellation."
        },
        {
            "id": "usage_reservations_reconcile",
            "upstream_operation_id": "usageReservations.reconcile",
            "method": "POST",
            "path": "/v1/usage/reservations/{reservationId}:reconcile",
            "auth": "account",
            "path_params": [
                "reservationId"
            ],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "orgId",
                "projectId",
                "environmentId",
                "configId",
                "reason",
                "observedUsage"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Hold maximum capacity and record non-secret evidence when exact provider usage is unavailable."
        },
        {
            "id": "list_grants",
            "upstream_operation_id": "listOAuthGrants",
            "method": "GET",
            "path": "/v1/oauth/grants",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List the OAuth grants the user has approved in the active workspace."
        },
        {
            "id": "revoke_grant",
            "upstream_operation_id": "revokeOAuthGrant",
            "method": "DELETE",
            "path": "/v1/oauth/grants/{id}",
            "auth": "account",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Revoke an OAuth grant and every refresh token issued under it."
        },
        {
            "id": "introspect_token",
            "upstream_operation_id": "introspectOAuthToken",
            "method": "POST",
            "path": "/v1/oauth/introspect",
            "auth": "introspectionSecret",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "token",
                "token_type_hint"
            ],
            "forbidden_body": [],
            "required_body": [
                "token"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Introspect a token or tp_ API key server-side; requires the introspection secret and returns {active: False} for anything invalid."
        },
        {
            "id": "discovery",
            "upstream_operation_id": "getOAuthAuthorizationServerMetadata",
            "method": "GET",
            "path": "/.well-known/oauth-authorization-server",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch OAuth 2.1 authorization-server metadata for the issuer."
        },
        {
            "id": "get_o_auth_protected_resource_metadata",
            "upstream_operation_id": "getOAuthProtectedResourceMetadata",
            "method": "GET",
            "path": "/.well-known/oauth-protected-resource",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "OAuth protected resource discovery metadata for MCP/resource clients."
        },
        {
            "id": "protected_resource_metadata",
            "upstream_operation_id": "getOAuthProtectedResourceMetadataForAudience",
            "method": "GET",
            "path": "/.well-known/oauth-protected-resource/{resource}",
            "auth": "none",
            "path_params": [
                "resource"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch OAuth protected-resource metadata for one registered audience."
        },
        {
            "id": "jwks",
            "upstream_operation_id": "getJsonWebKeySet",
            "method": "GET",
            "path": "/.well-known/jwks.json",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the JSON Web Key Set used to verify control-plane access tokens."
        },
        {
            "id": "admin_operational_provenance",
            "upstream_operation_id": "adminOperationalProvenance",
            "method": "GET",
            "path": "/v1/admin/operations/provenance",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Return fail-closed source, machine, and image provenance for the serving runtime to a platform-staff account session."
        },
        {
            "id": "admin_step_up",
            "upstream_operation_id": "adminStepUp",
            "method": "POST",
            "path": "/v1/admin/step-up",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "password"
            ],
            "forbidden_body": [],
            "required_body": [
                "password"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Re-authenticate a platform-staff account session to mint a short-lived step-up elevation required for sensitive admin mutations."
        },
        {
            "id": "admin_adjust_credits",
            "upstream_operation_id": "adminAdjustCredits",
            "method": "POST",
            "path": "/v1/admin/billing/credits/adjust",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "orgId",
                "creditMicros",
                "reference",
                "reason"
            ],
            "forbidden_body": [],
            "required_body": [
                "orgId",
                "creditMicros"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Platform-staff credit grant/adjustment to an org wallet. Requires a fresh step-up elevation; idempotent on the reference."
        },
        {
            "id": "admin_billing_orgs",
            "upstream_operation_id": "adminBillingOrgs",
            "method": "GET",
            "path": "/v1/admin/billing/orgs",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Platform-staff internal billing view: per-org wallet balances plus provider cost, customer charge, and margin economics."
        },
        {
            "id": "github_setup_sessions_create",
            "upstream_operation_id": "githubSetupSessions.create",
            "method": "POST",
            "path": "/v1/github/setup-sessions",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "projectId",
                "environmentId",
                "returnUrl"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Create a one-time CSRF-bound GitHub App installation session."
        },
        {
            "id": "github_setup_sessions_complete",
            "upstream_operation_id": "githubSetupSessions.complete",
            "method": "GET",
            "path": "/github/callback",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "state",
                "installation_id"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Bind a GitHub installation callback to its authenticated workspace."
        },
        {
            "id": "github_installations_list",
            "upstream_operation_id": "githubInstallations.list",
            "method": "GET",
            "path": "/v1/github/installations",
            "auth": "account",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List active GitHub App installations for the organization."
        },
        {
            "id": "github_installations_disconnect",
            "upstream_operation_id": "githubInstallations.disconnect",
            "method": "DELETE",
            "path": "/v1/github/installations/{installationId}",
            "auth": "account",
            "path_params": [
                "installationId"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Disconnect a GitHub App installation from the workspace."
        },
        {
            "id": "github_installation_repositories_list",
            "upstream_operation_id": "githubInstallationRepositories.list",
            "method": "GET",
            "path": "/v1/github/installations/{installationId}/repositories",
            "auth": "account",
            "path_params": [
                "installationId"
            ],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List repository metadata received for a GitHub installation."
        },
        {
            "id": "github_repository_snapshots_capture",
            "upstream_operation_id": "githubRepositorySnapshots.capture",
            "method": "POST",
            "path": "/v1/github/installations/{installationId}/repositories/{repositoryId}:snapshot",
            "auth": "account",
            "path_params": [
                "installationId",
                "repositoryId"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "ref"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Capture an ephemeral, immutable GitHub repository snapshot for an authorized workspace."
        },
        {
            "id": "github_webhooks_accept",
            "upstream_operation_id": "githubWebhooks.accept",
            "method": "POST",
            "path": "/github/webhook",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Accept a signed, replay-deduplicated GitHub webhook."
        }
    ],
    "palette": [
        {
            "id": "health",
            "upstream_operation_id": "health.check",
            "method": "GET",
            "path": "/health",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check palette API liveness; returns {ok: True}."
        },
        {
            "id": "alerts_evaluate",
            "upstream_operation_id": "alerts.evaluate",
            "method": "POST",
            "path": "/v1/alerts/{tenant_id}/{project_id}/traces/{trace_id}/webhook",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "trace_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "input",
                "policy"
            ],
            "forbidden_body": [],
            "required_body": [
                "policy",
                "input"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/alerts/{tenant_id}/{project_id}/traces/{trace_id}/webhook."
        },
        {
            "id": "create_api_key",
            "upstream_operation_id": "apiKeys.create",
            "method": "POST",
            "path": "/v1/api-keys/{tenant_id}/{project_id}/{environment_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "environment_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "scopes"
            ],
            "forbidden_body": [],
            "required_body": [
                "scopes"
            ],
            "body_defaults": {},
            "scope": "admin",
            "description": "Mint a palette-scoped API key; the secret is returned exactly once."
        },
        {
            "id": "revoke_api_key",
            "upstream_operation_id": "apiKeys.revoke",
            "method": "POST",
            "path": "/v1/api-keys/{tenant_id}/{project_id}/{environment_id}/{api_key_id}/revoke",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "environment_id",
                "api_key_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "admin",
            "description": "Revoke a palette API key."
        },
        {
            "id": "archive_query_spans",
            "upstream_operation_id": "archive.querySpans",
            "method": "GET",
            "path": "/v1/archive/{tenant_id}/{project_id}/spans",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [
                "environment_id",
                "trace_id",
                "span_id",
                "kind",
                "status",
                "limit"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/archive/{tenant_id}/{project_id}/spans."
        },
        {
            "id": "archive_trace",
            "upstream_operation_id": "archive.archiveTrace",
            "method": "POST",
            "path": "/v1/archive/{tenant_id}/{project_id}/{trace_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "trace_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:read",
            "description": "Archive a trace to Parquet and return the archive manifest."
        },
        {
            "id": "audit_list",
            "upstream_operation_id": "audit.list",
            "method": "GET",
            "path": "/v1/audit/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/audit/{tenant_id}/{project_id}."
        },
        {
            "id": "calibrations_run",
            "upstream_operation_id": "calibrations.run",
            "method": "POST",
            "path": "/v1/calibrations/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "dataset_id",
                "version_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "eval_report_id",
                "evaluator_version_id",
                "pass_threshold"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/calibrations/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}."
        },
        {
            "id": "connect_get_status",
            "upstream_operation_id": "connect.getStatus",
            "method": "GET",
            "path": "/v1/connect/status/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/connect/status/{tenant_id}/{project_id}."
        },
        {
            "id": "connectors_list",
            "upstream_operation_id": "connectors.list",
            "method": "GET",
            "path": "/v1/connectors/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [
                "limit"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/connectors/{tenant_id}/{project_id}."
        },
        {
            "id": "connectors_connect",
            "upstream_operation_id": "connectors.connect",
            "method": "POST",
            "path": "/v1/connectors/{tenant_id}/{project_id}/connect",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "toolkit"
            ],
            "forbidden_body": [],
            "required_body": [
                "toolkit"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/connectors/{tenant_id}/{project_id}/connect."
        },
        {
            "id": "connectors_invoke_tool",
            "upstream_operation_id": "connectors.invokeTool",
            "method": "POST",
            "path": "/v1/connectors/{tenant_id}/{project_id}/invoke",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "arguments",
                "tool"
            ],
            "forbidden_body": [],
            "required_body": [
                "tool"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/connectors/{tenant_id}/{project_id}/invoke."
        },
        {
            "id": "connectors_get_skills",
            "upstream_operation_id": "connectors.getSkills",
            "method": "GET",
            "path": "/v1/connectors/{tenant_id}/{project_id}/skills",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [
                "toolkit"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/connectors/{tenant_id}/{project_id}/skills."
        },
        {
            "id": "connectors_status",
            "upstream_operation_id": "connectors.status",
            "method": "GET",
            "path": "/v1/connectors/{tenant_id}/{project_id}/status",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [
                "toolkit"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/connectors/{tenant_id}/{project_id}/status."
        },
        {
            "id": "connectors_list_tools",
            "upstream_operation_id": "connectors.listTools",
            "method": "GET",
            "path": "/v1/connectors/{tenant_id}/{project_id}/tools",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [
                "toolkit",
                "limit"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/connectors/{tenant_id}/{project_id}/tools."
        },
        {
            "id": "create_dataset",
            "upstream_operation_id": "datasets.create",
            "method": "POST",
            "path": "/v1/datasets/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "name"
            ],
            "forbidden_body": [],
            "required_body": [
                "name"
            ],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Create a dataset for curating cases from traces."
        },
        {
            "id": "promote_trace_to_case",
            "upstream_operation_id": "datasets.promoteCaseFromTrace",
            "method": "POST",
            "path": "/v1/datasets/{tenant_id}/{project_id}/{dataset_id}/cases/from-trace",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "dataset_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "reference",
                "span_id",
                "trace_id"
            ],
            "forbidden_body": [],
            "required_body": [
                "trace_id"
            ],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Promote a trace (or one span of it) into a dataset case."
        },
        {
            "id": "create_dataset_version",
            "upstream_operation_id": "datasets.createVersion",
            "method": "POST",
            "path": "/v1/datasets/{tenant_id}/{project_id}/{dataset_id}/versions",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "dataset_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "case_ids"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Snapshot a dataset into an immutable version for evals and experiments."
        },
        {
            "id": "evals_run_deterministic",
            "upstream_operation_id": "evals.runDeterministic",
            "method": "POST",
            "path": "/v1/datasets/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/evals/deterministic",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "dataset_id",
                "version_id"
            ],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "evaluator_id",
                "evaluator_version_id",
                "agent_release_id",
                "kind"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/datasets/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/evals/deterministic."
        },
        {
            "id": "evals_run_judge",
            "upstream_operation_id": "evals.runJudge",
            "method": "POST",
            "path": "/v1/datasets/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/evals/judge",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "dataset_id",
                "version_id"
            ],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "evaluator_id",
                "evaluator_version_id",
                "agent_release_id",
                "kind",
                "provider_secret_id"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/datasets/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/evals/judge."
        },
        {
            "id": "import_tempera_bundle",
            "upstream_operation_id": "evalResults.importTemperaBundle",
            "method": "POST",
            "path": "/v1/eval-results/{tenant_id}/{project_id}/tempera/bundles",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "canonical_json",
                "public_key_pem",
                "signature_base64"
            ],
            "forbidden_body": [],
            "required_body": [
                "canonical_json",
                "signature_base64",
                "public_key_pem"
            ],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Import one RFC 8785-canonical, detached-Ed25519-signed official Tempera result bundle and return its minimal evidence receipt."
        },
        {
            "id": "record_tempera_decision",
            "upstream_operation_id": "evalResults.recordTemperaDecision",
            "method": "POST",
            "path": "/v1/eval-results/{tenant_id}/{project_id}/tempera/decisions",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "canonical_json",
                "public_key_pem",
                "signature_base64"
            ],
            "forbidden_body": [],
            "required_body": [
                "canonical_json",
                "signature_base64",
                "public_key_pem"
            ],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Import one RFC 8785-canonical, detached-Ed25519-signed preregistered Tempera A/B decision and return its minimal evidence receipt."
        },
        {
            "id": "get_tempera_evidence",
            "upstream_operation_id": "evalResults.getTemperaEvidence",
            "method": "GET",
            "path": "/v1/eval-results/{tenant_id}/{project_id}/tempera/{kind}/{external_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "kind",
                "external_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Fetch one tenant/project-scoped Tempera evidence receipt without returning its raw signed payload."
        },
        {
            "id": "experiments_run_deterministic",
            "upstream_operation_id": "experiments.runDeterministic",
            "method": "POST",
            "path": "/v1/experiments/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/deterministic",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "dataset_id",
                "version_id"
            ],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "baseline_release_id",
                "candidate_release_id",
                "evaluator_id",
                "evaluator_version_id",
                "kind",
                "baseline_outputs",
                "candidate_outputs"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/experiments/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/deterministic."
        },
        {
            "id": "experiments_run_judge",
            "upstream_operation_id": "experiments.runJudge",
            "method": "POST",
            "path": "/v1/experiments/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/judge",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "dataset_id",
                "version_id"
            ],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "baseline_release_id",
                "candidate_release_id",
                "evaluator_id",
                "evaluator_version_id",
                "kind",
                "baseline_outputs",
                "candidate_outputs",
                "provider_secret_id"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/experiments/{tenant_id}/{project_id}/{dataset_id}/versions/{version_id}/judge."
        },
        {
            "id": "gates_create",
            "upstream_operation_id": "gates.create",
            "method": "POST",
            "path": "/v1/gates/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "dataset_id",
                "evaluator_version_id",
                "gate_id",
                "inconclusive_policy",
                "name"
            ],
            "forbidden_body": [],
            "required_body": [
                "gate_id",
                "name"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/gates/{tenant_id}/{project_id}."
        },
        {
            "id": "gates_run",
            "upstream_operation_id": "gates.run",
            "method": "POST",
            "path": "/v1/gates/{tenant_id}/{project_id}/{gate_id}/run",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "gate_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "experiment_run_id"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/gates/{tenant_id}/{project_id}/{gate_id}/run."
        },
        {
            "id": "import_source",
            "upstream_operation_id": "ingest.importSource",
            "method": "POST",
            "path": "/v1/import/{tenant_id}/{project_id}/{environment_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "environment_id"
            ],
            "path_param_templates": {},
            "query": [
                "durability"
            ],
            "body": [
                "payload",
                "source"
            ],
            "forbidden_body": [],
            "required_body": [
                "source"
            ],
            "body_defaults": {},
            "scope": "trace:write",
            "description": "Import spans from a named external source payload."
        },
        {
            "id": "ingest_replay_dead_letter",
            "upstream_operation_id": "ingest.replayDeadLetter",
            "method": "POST",
            "path": "/v1/ingest/{tenant_id}/{project_id}/dead-letters/{message_id}/replay",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "message_id"
            ],
            "path_param_templates": {},
            "query": [
                "reset_attempts"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/ingest/{tenant_id}/{project_id}/dead-letters/{message_id}/replay."
        },
        {
            "id": "ingest_get_queue_status",
            "upstream_operation_id": "ingest.getQueueStatus",
            "method": "GET",
            "path": "/v1/ingest/{tenant_id}/{project_id}/queue",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/ingest/{tenant_id}/{project_id}/queue."
        },
        {
            "id": "ingest_drain_trace_ingested",
            "upstream_operation_id": "ingest.drainTraceIngested",
            "method": "POST",
            "path": "/v1/ingest/{tenant_id}/{project_id}/trace-ingested/drain",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [
                "limit"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/ingest/{tenant_id}/{project_id}/trace-ingested/drain."
        },
        {
            "id": "ingest_drain_trace_writes",
            "upstream_operation_id": "ingest.drainTraceWrites",
            "method": "POST",
            "path": "/v1/ingest/{tenant_id}/{project_id}/trace-writes/drain",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [
                "limit"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/ingest/{tenant_id}/{project_id}/trace-writes/drain."
        },
        {
            "id": "ingest_reconcile_trace",
            "upstream_operation_id": "ingest.reconcileTrace",
            "method": "POST",
            "path": "/v1/ingest/{tenant_id}/{project_id}/traces/{trace_id}/reconcile",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "trace_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/ingest/{tenant_id}/{project_id}/traces/{trace_id}/reconcile."
        },
        {
            "id": "judge_evaluate",
            "upstream_operation_id": "judge.evaluate",
            "method": "POST",
            "path": "/v1/judge/{tenant_id}/{project_id}/evaluate",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "cache_namespace",
                "case",
                "evaluator",
                "provider_secret_id"
            ],
            "forbidden_body": [],
            "required_body": [
                "evaluator",
                "case",
                "provider_secret_id"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/judge/{tenant_id}/{project_id}/evaluate."
        },
        {
            "id": "judge_list_ledger",
            "upstream_operation_id": "judge.listLedger",
            "method": "GET",
            "path": "/v1/judge/{tenant_id}/{project_id}/ledger",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/judge/{tenant_id}/{project_id}/ledger."
        },
        {
            "id": "online_decide_sampling",
            "upstream_operation_id": "online.decideSampling",
            "method": "POST",
            "path": "/v1/online/{tenant_id}/{project_id}/traces/{trace_id}/sampling",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "trace_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "high_cost_micros_threshold",
                "keep_errors",
                "sample_rate_per_mille",
                "slow_ms_threshold"
            ],
            "forbidden_body": [],
            "required_body": [
                "sample_rate_per_mille",
                "keep_errors"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/online/{tenant_id}/{project_id}/traces/{trace_id}/sampling."
        },
        {
            "id": "prompts_list",
            "upstream_operation_id": "prompts.list",
            "method": "GET",
            "path": "/v1/prompts/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/prompts/{tenant_id}/{project_id}."
        },
        {
            "id": "prompts_create",
            "upstream_operation_id": "prompts.create",
            "method": "POST",
            "path": "/v1/prompts/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "created_by",
                "description",
                "message",
                "name",
                "template"
            ],
            "forbidden_body": [],
            "required_body": [
                "name",
                "template"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/prompts/{tenant_id}/{project_id}."
        },
        {
            "id": "prompts_get",
            "upstream_operation_id": "prompts.get",
            "method": "GET",
            "path": "/v1/prompts/{tenant_id}/{project_id}/{prompt_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "prompt_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/prompts/{tenant_id}/{project_id}/{prompt_id}."
        },
        {
            "id": "prompts_diff_versions",
            "upstream_operation_id": "prompts.diffVersions",
            "method": "GET",
            "path": "/v1/prompts/{tenant_id}/{project_id}/{prompt_id}/diff",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "prompt_id"
            ],
            "path_param_templates": {},
            "query": [
                "from",
                "to"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/prompts/{tenant_id}/{project_id}/{prompt_id}/diff."
        },
        {
            "id": "prompts_list_versions",
            "upstream_operation_id": "prompts.listVersions",
            "method": "GET",
            "path": "/v1/prompts/{tenant_id}/{project_id}/{prompt_id}/versions",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "prompt_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/prompts/{tenant_id}/{project_id}/{prompt_id}/versions."
        },
        {
            "id": "prompts_add_version",
            "upstream_operation_id": "prompts.addVersion",
            "method": "POST",
            "path": "/v1/prompts/{tenant_id}/{project_id}/{prompt_id}/versions",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "prompt_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "created_by",
                "message",
                "template"
            ],
            "forbidden_body": [],
            "required_body": [
                "template"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/prompts/{tenant_id}/{project_id}/{prompt_id}/versions."
        },
        {
            "id": "provider_secrets_list",
            "upstream_operation_id": "providerSecrets.list",
            "method": "GET",
            "path": "/v1/provider-secrets/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/provider-secrets/{tenant_id}/{project_id}."
        },
        {
            "id": "provider_secrets_create",
            "upstream_operation_id": "providerSecrets.create",
            "method": "POST",
            "path": "/v1/provider-secrets/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "display_name",
                "provider",
                "secret_value"
            ],
            "forbidden_body": [],
            "required_body": [
                "provider",
                "display_name",
                "secret_value"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/provider-secrets/{tenant_id}/{project_id}."
        },
        {
            "id": "provider_secrets_revoke",
            "upstream_operation_id": "providerSecrets.revoke",
            "method": "POST",
            "path": "/v1/provider-secrets/{tenant_id}/{project_id}/{provider_secret_id}/revoke",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "provider_secret_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/provider-secrets/{tenant_id}/{project_id}/{provider_secret_id}/revoke."
        },
        {
            "id": "reviews_create_queue",
            "upstream_operation_id": "reviews.createQueue",
            "method": "POST",
            "path": "/v1/review-queues/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "annotation_schema",
                "name",
                "queue_id"
            ],
            "forbidden_body": [],
            "required_body": [
                "name",
                "annotation_schema"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/review-queues/{tenant_id}/{project_id}."
        },
        {
            "id": "reviews_list_tasks",
            "upstream_operation_id": "reviews.listTasks",
            "method": "GET",
            "path": "/v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "queue_id"
            ],
            "path_param_templates": {},
            "query": [
                "state"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks."
        },
        {
            "id": "reviews_enqueue_task_from_trace",
            "upstream_operation_id": "reviews.enqueueTaskFromTrace",
            "method": "POST",
            "path": "/v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks/from-trace",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "queue_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "dataset_case_id",
                "dataset_id",
                "priority",
                "span_id",
                "task_id",
                "trace_id"
            ],
            "forbidden_body": [],
            "required_body": [
                "trace_id"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks/from-trace."
        },
        {
            "id": "reviews_submit_annotation",
            "upstream_operation_id": "reviews.submitAnnotation",
            "method": "POST",
            "path": "/v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks/{task_id}/annotations",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "queue_id",
                "task_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "annotation_id",
                "payload",
                "reviewer_id",
                "verdict"
            ],
            "forbidden_body": [],
            "required_body": [
                "reviewer_id",
                "verdict",
                "payload"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks/{task_id}/annotations."
        },
        {
            "id": "reviews_promote_annotation",
            "upstream_operation_id": "reviews.promoteAnnotation",
            "method": "POST",
            "path": "/v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks/{task_id}/annotations/{annotation_id}/promote",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "queue_id",
                "task_id",
                "annotation_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "dataset_id",
                "reference"
            ],
            "forbidden_body": [],
            "required_body": [
                "dataset_id"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/review-queues/{tenant_id}/{project_id}/{queue_id}/tasks/{task_id}/annotations/{annotation_id}/promote."
        },
        {
            "id": "scenarios_list",
            "upstream_operation_id": "scenarios.list",
            "method": "GET",
            "path": "/v1/scenarios/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/scenarios/{tenant_id}/{project_id}."
        },
        {
            "id": "scenarios_create",
            "upstream_operation_id": "scenarios.create",
            "method": "POST",
            "path": "/v1/scenarios/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "exemplar_trace_id",
                "expected_outcome",
                "failure_mode",
                "source_trace_ids",
                "title"
            ],
            "forbidden_body": [],
            "required_body": [
                "title",
                "source_trace_ids"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/scenarios/{tenant_id}/{project_id}."
        },
        {
            "id": "scenarios_mine",
            "upstream_operation_id": "scenarios.mine",
            "method": "POST",
            "path": "/v1/scenarios/{tenant_id}/{project_id}/mine",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "jaccard_threshold",
                "trace_ids"
            ],
            "forbidden_body": [],
            "required_body": [
                "trace_ids"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/scenarios/{tenant_id}/{project_id}/mine."
        },
        {
            "id": "scenarios_get",
            "upstream_operation_id": "scenarios.get",
            "method": "GET",
            "path": "/v1/scenarios/{tenant_id}/{project_id}/{scenario_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id",
                "scenario_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/scenarios/{tenant_id}/{project_id}/{scenario_id}."
        },
        {
            "id": "search_spans",
            "upstream_operation_id": "search.spans",
            "method": "GET",
            "path": "/v1/search/{tenant_id}/spans",
            "auth": "product",
            "path_params": [
                "tenant_id"
            ],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:read",
            "description": "Search spans by text query and facet filters."
        },
        {
            "id": "get_span",
            "upstream_operation_id": "spans.get",
            "method": "GET",
            "path": "/v1/spans/{tenant_id}/{trace_id}/{span_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "trace_id",
                "span_id"
            ],
            "path_param_templates": {},
            "query": [
                "unmask",
                "reason"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:read",
            "description": "Fetch one canonical span by trace and span id."
        },
        {
            "id": "get_span_io",
            "upstream_operation_id": "spans.getIo",
            "method": "GET",
            "path": "/v1/spans/{tenant_id}/{trace_id}/{span_id}/io",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "trace_id",
                "span_id"
            ],
            "path_param_templates": {},
            "query": [
                "unmask",
                "reason"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:read",
            "description": "Fetch a span's recorded input and output values."
        },
        {
            "id": "ingest_span",
            "upstream_operation_id": "ingest.native",
            "method": "POST",
            "path": "/v1/traces/native",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
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
            "body_defaults": {},
            "scope": "trace:write",
            "description": "Ingest one native span; idempotent when an idempotency key is supplied."
        },
        {
            "id": "list_traces",
            "upstream_operation_id": "traces.list",
            "method": "GET",
            "path": "/v1/traces/{tenant_id}",
            "auth": "product",
            "path_params": [
                "tenant_id"
            ],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:read",
            "description": "List trace summaries for a tenant with filters and cursor pagination."
        },
        {
            "id": "get_trace",
            "upstream_operation_id": "traces.get",
            "method": "GET",
            "path": "/v1/traces/{tenant_id}/{trace_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "trace_id"
            ],
            "path_param_templates": {},
            "query": [
                "unmask",
                "reason"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "trace:read",
            "description": "Fetch one full trace with all canonical spans; unmasking PII requires the pii:unmask scope and a reason."
        },
        {
            "id": "get_usage_summary",
            "upstream_operation_id": "usage.getSummary",
            "method": "GET",
            "path": "/v1/usage/{tenant_id}/{project_id}",
            "auth": "product",
            "path_params": [
                "tenant_id",
                "project_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "admin",
            "description": "Fetch usage totals for a tenant project."
        }
    ],
    "tempo": [
        {
            "id": "agent_card",
            "upstream_operation_id": "agentCard",
            "method": "GET",
            "path": "/.well-known/agent-card.json",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /.well-known/agent-card.json."
        },
        {
            "id": "agent_json",
            "upstream_operation_id": "agentJson",
            "method": "GET",
            "path": "/.well-known/agent.json",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /.well-known/agent.json."
        },
        {
            "id": "drain",
            "upstream_operation_id": "drain",
            "method": "POST",
            "path": "/drain",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /drain."
        },
        {
            "id": "health",
            "upstream_operation_id": "health",
            "method": "GET",
            "path": "/health",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check tempod liveness; returns {ok: True}."
        },
        {
            "id": "metrics",
            "upstream_operation_id": "metrics",
            "method": "GET",
            "path": "/metrics",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /metrics."
        },
        {
            "id": "openapi",
            "upstream_operation_id": "openapi",
            "method": "GET",
            "path": "/openapi.json",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch tempod's OpenAPI document, generated at runtime for this host."
        },
        {
            "id": "ready",
            "upstream_operation_id": "ready",
            "method": "GET",
            "path": "/ready",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check tempod readiness, including engine attachment, drain state, and session capacity."
        },
        {
            "id": "list_runs",
            "upstream_operation_id": "listRuns",
            "method": "GET",
            "path": "/runs",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "session_id"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List agent runs, optionally filtered to one session."
        },
        {
            "id": "get_run",
            "upstream_operation_id": "getRun",
            "method": "GET",
            "path": "/runs/{run_id}",
            "auth": "product",
            "path_params": [
                "run_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch one agent run with its state."
        },
        {
            "id": "cancel_run",
            "upstream_operation_id": "cancelRun",
            "method": "POST",
            "path": "/runs/{run_id}/cancel",
            "auth": "product",
            "path_params": [
                "run_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Cancel an agent run."
        },
        {
            "id": "run_events",
            "upstream_operation_id": "runEvents",
            "method": "GET",
            "path": "/runs/{run_id}/events",
            "auth": "product",
            "path_params": [
                "run_id"
            ],
            "path_param_templates": {},
            "query": [
                "after_seq"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /runs/{run_id}/events."
        },
        {
            "id": "resume_run",
            "upstream_operation_id": "resumeRun",
            "method": "POST",
            "path": "/runs/{run_id}/resume",
            "auth": "product",
            "path_params": [
                "run_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Resume an agent run after a human handoff completes."
        },
        {
            "id": "list_sessions",
            "upstream_operation_id": "listSessions",
            "method": "GET",
            "path": "/sessions",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List browser sessions with their state and creation time."
        },
        {
            "id": "create_session",
            "upstream_operation_id": "createSession",
            "method": "POST",
            "path": "/sessions",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "driverless",
                "url"
            ],
            "forbidden_body": [],
            "required_body": [
                "url"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Open a browser session at a URL; driverless sessions skip engine attachment."
        },
        {
            "id": "close_session",
            "upstream_operation_id": "closeSession",
            "method": "DELETE",
            "path": "/sessions/{session_id}",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Close a browser session and release its engine resources."
        },
        {
            "id": "act_batch",
            "upstream_operation_id": "actBatchSession",
            "method": "POST",
            "path": "/sessions/{session_id}/act_batch",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "batch",
                "confirmation_grant",
                "confirmed",
                "idempotency_key",
                "input_tainted",
                "payment_context"
            ],
            "forbidden_body": [],
            "required_body": [
                "batch"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Apply a batch of semantic actions with policy gating; returns the applied diff or a policy decision."
        },
        {
            "id": "adopt_session",
            "upstream_operation_id": "adoptSession",
            "method": "POST",
            "path": "/sessions/{session_id}/adopt",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "engine_tier",
                "label",
                "platform",
                "profile_id",
                "storage_continuity",
                "surface_id"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Let a human surface take write ownership of the session and receive an adoption lease."
        },
        {
            "id": "grant_confirmation",
            "upstream_operation_id": "grantSessionConfirmation",
            "method": "POST",
            "path": "/sessions/{session_id}/confirmations/{confirmation_id}",
            "auth": "product",
            "path_params": [
                "session_id",
                "confirmation_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Grant a pending policy confirmation and receive a single-use grant token."
        },
        {
            "id": "session_events",
            "upstream_operation_id": "sessionEvents",
            "method": "GET",
            "path": "/sessions/{session_id}/events",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "path_param_templates": {},
            "query": [
                "after_seq"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the session's event window after a sequence number."
        },
        {
            "id": "handoff_session",
            "upstream_operation_id": "handoffSession",
            "method": "POST",
            "path": "/sessions/{session_id}/handoff",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Return write ownership of the session to the agent plane."
        },
        {
            "id": "manager_session",
            "upstream_operation_id": "managerSession",
            "method": "GET",
            "path": "/sessions/{session_id}/manager",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /sessions/{session_id}/manager."
        },
        {
            "id": "observe",
            "upstream_operation_id": "observeSession",
            "method": "GET",
            "path": "/sessions/{session_id}/observe",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the session's compiled structured observation (ranked, stably-identified elements)."
        },
        {
            "id": "create_run",
            "upstream_operation_id": "createSessionRun",
            "method": "POST",
            "path": "/sessions/{session_id}/runs",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "actions",
                "goal",
                "max_rounds",
                "token_budget"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Start an agent run against the session with a goal, action budget, and round limit."
        },
        {
            "id": "screenshot",
            "upstream_operation_id": "screenshotSession",
            "method": "GET",
            "path": "/sessions/{session_id}/screenshot",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "path_param_templates": {},
            "query": [
                "set_of_marks"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Capture a PNG screenshot of the session, optionally annotated with set-of-marks."
        },
        {
            "id": "register_session_surface",
            "upstream_operation_id": "registerSessionSurface",
            "method": "POST",
            "path": "/sessions/{session_id}/surfaces",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "engine_tier",
                "label",
                "platform",
                "profile_id",
                "storage_continuity",
                "surface_id"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /sessions/{session_id}/surfaces."
        },
        {
            "id": "remove_session_surface",
            "upstream_operation_id": "removeSessionSurface",
            "method": "DELETE",
            "path": "/sessions/{session_id}/surfaces/{surface_id}",
            "auth": "product",
            "path_params": [
                "session_id",
                "surface_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call DELETE /sessions/{session_id}/surfaces/{surface_id}."
        },
        {
            "id": "transform_session",
            "upstream_operation_id": "transformSession",
            "method": "POST",
            "path": "/sessions/{session_id}/transform",
            "auth": "product",
            "path_params": [
                "session_id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "determinism",
                "idempotency_key",
                "input",
                "lane",
                "source",
                "spans"
            ],
            "forbidden_body": [],
            "required_body": [
                "lane",
                "source"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /sessions/{session_id}/transform."
        }
    ],
    "temperaLlm": [
        {
            "id": "health",
            "upstream_operation_id": "health.check",
            "method": "GET",
            "path": "/healthz",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check tempera-llm gateway liveness; returns {ok: True}."
        },
        {
            "id": "readiness_check",
            "upstream_operation_id": "readiness.check",
            "method": "GET",
            "path": "/readyz",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /readyz."
        },
        {
            "id": "create_chat_completion",
            "upstream_operation_id": "chatCompletions.create",
            "method": "POST",
            "path": "/v1/chat/completions",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "model",
                "messages",
                "max_tokens"
            ],
            "body_defaults": {},
            "scope": "model:invoke",
            "description": "Create a non-streaming OpenAI-compatible chat completion through the tempera-llm gateway."
        },
        {
            "id": "list_models",
            "upstream_operation_id": "models.list",
            "method": "GET",
            "path": "/v1/models",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "model:read",
            "description": "List the configured model catalog the gateway can route to."
        },
        {
            "id": "create_response",
            "upstream_operation_id": "responses.create",
            "method": "POST",
            "path": "/v1/responses",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "byok",
                "input",
                "max_output_tokens",
                "model",
                "response_format"
            ],
            "forbidden_body": [],
            "required_body": [
                "model",
                "input",
                "max_output_tokens"
            ],
            "body_defaults": {},
            "scope": "model:invoke",
            "description": "Create a non-streaming OpenAI Responses-style inference request through the tempera-llm gateway."
        }
    ],
    "temperaWorkflows": [
        {
            "id": "health",
            "upstream_operation_id": "healthz",
            "method": "GET",
            "path": "/healthz",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check tempera-workflows engine liveness."
        },
        {
            "id": "list_node_types",
            "upstream_operation_id": "nodeTypes.list",
            "method": "GET",
            "path": "/v1/node-types",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:read",
            "description": "List the typed node catalog: native orchestration nodes plus the sdk.<product>.<operation> nodes generated from the SDK surface."
        },
        {
            "id": "list_runs",
            "upstream_operation_id": "runs.list",
            "method": "GET",
            "path": "/v1/runs",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "workflowId",
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:read",
            "description": "List workflow runs, optionally filtered to one workflow."
        },
        {
            "id": "get_run",
            "upstream_operation_id": "runs.get",
            "method": "GET",
            "path": "/v1/runs/{runId}",
            "auth": "product",
            "path_params": [
                "runId"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:read",
            "description": "Fetch one workflow run with its state, node results, and timings; the live SSE event stream at /v1/runs/{run_id}/events is passthrough-only."
        },
        {
            "id": "cancel_run",
            "upstream_operation_id": "runs.cancel",
            "method": "POST",
            "path": "/v1/runs/{runId}:cancel",
            "auth": "product",
            "path_params": [
                "runId"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:run",
            "description": "Cancel a queued or running workflow run."
        },
        {
            "id": "list_workflows",
            "upstream_operation_id": "workflows.list",
            "method": "GET",
            "path": "/v1/workflows",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:read",
            "description": "List stored workflow definitions, newest first."
        },
        {
            "id": "create_workflow",
            "upstream_operation_id": "workflows.create",
            "method": "POST",
            "path": "/v1/workflows",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
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
            "upstream_operation_id": "workflows.get",
            "method": "GET",
            "path": "/v1/workflows/{workflowId}",
            "auth": "product",
            "path_params": [
                "workflowId"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:read",
            "description": "Fetch one stored workflow definition."
        },
        {
            "id": "delete_workflow",
            "upstream_operation_id": "workflows.delete",
            "method": "DELETE",
            "path": "/v1/workflows/{workflowId}",
            "auth": "product",
            "path_params": [
                "workflowId"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:write",
            "description": "Delete a stored workflow definition."
        },
        {
            "id": "update_workflow",
            "upstream_operation_id": "workflows.update",
            "method": "PATCH",
            "path": "/v1/workflows/{workflowId}",
            "auth": "product",
            "path_params": [
                "workflowId"
            ],
            "path_param_templates": {},
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
            "forbidden_body": [],
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
            "id": "create_run",
            "upstream_operation_id": "runs.create",
            "method": "POST",
            "path": "/v1/workflows/{workflowId}/runs",
            "auth": "product",
            "path_params": [
                "workflowId"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "idempotencyKey",
                "input",
                "only",
                "seedOutputs",
                "startAt",
                "usePinned"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:run",
            "description": "Start a run of a stored workflow with an optional input document and idempotency key."
        },
        {
            "id": "call_workflow",
            "upstream_operation_id": "workflows.call",
            "method": "POST",
            "path": "/v1/workflows/{workflowId}:call",
            "auth": "product",
            "path_params": [
                "workflowId"
            ],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "workflow:run",
            "description": "Run a workflow to completion and return its output in a single call."
        },
        {
            "id": "compose_workflow",
            "upstream_operation_id": "workflows.compose",
            "method": "POST",
            "path": "/v1/workflows/{workflowId}:compose",
            "auth": "product",
            "path_params": [
                "workflowId"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "attachments",
                "draft",
                "history",
                "model",
                "prompt"
            ],
            "forbidden_body": [],
            "required_body": [
                "prompt"
            ],
            "body_defaults": {},
            "scope": "workflow:write",
            "description": "Search the full SDK-backed node catalog or ask Tempera Code to propose a validated workflow draft without saving or running it."
        },
        {
            "id": "assist_json",
            "upstream_operation_id": "workflows.assistJson",
            "method": "POST",
            "path": "/v1/workflows:assistJson",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "context",
                "current",
                "expectedRoot",
                "mode",
                "prompt",
                "purpose"
            ],
            "forbidden_body": [],
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
            "id": "validate_workflow",
            "upstream_operation_id": "workflows.validate",
            "method": "POST",
            "path": "/v1/workflows:validate",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
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
        }
    ],
    "temperaGym": [
        {
            "id": "health",
            "upstream_operation_id": "health.get",
            "method": "GET",
            "path": "/healthz",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check tempera-gym service liveness."
        },
        {
            "id": "list_environments",
            "upstream_operation_id": "environments.list",
            "method": "GET",
            "path": "/v1/environments",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List the gym pack's environment catalog, including implementation status and per-environment manifests."
        },
        {
            "id": "list_runs",
            "upstream_operation_id": "runs.list",
            "method": "GET",
            "path": "/v1/runs",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "environmentId",
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List persisted rollout run index records, newest first."
        },
        {
            "id": "get_run",
            "upstream_operation_id": "runs.get",
            "method": "GET",
            "path": "/v1/runs/{run}",
            "auth": "product",
            "path_params": [
                "run"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one persisted run's index record and verified trajectory-v1 envelope by run id or trajectory content hash."
        },
        {
            "id": "create_rollout",
            "upstream_operation_id": "rollouts.create",
            "method": "POST",
            "path": "/v1/rollouts",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "environmentId",
                "seed"
            ],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Execute one rollout synchronously, persist the trajectory, and return the completed operation envelope."
        }
    ],
    "cradle": [
        {
            "id": "projects_browser_adapters_issue_capability",
            "upstream_operation_id": "projects.browserAdapters.issueCapability",
            "method": "POST",
            "path": "/v1/browser/adapter/capability",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "actor",
                "adapter_id",
                "sensitive_activity_mode",
                "sensitivity",
                "ttl_seconds"
            ],
            "forbidden_body": [],
            "required_body": [
                "actor",
                "sensitivity"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/browser/adapter/capability."
        },
        {
            "id": "projects_browser_adapters_validate_completion",
            "upstream_operation_id": "projects.browserAdapters.validateCompletion",
            "method": "POST",
            "path": "/v1/browser/adapter/completion/validate",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
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
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/browser/adapter/completion/validate."
        },
        {
            "id": "get_browser_adapter_contract",
            "upstream_operation_id": "projects.browserAdapters.getContract",
            "method": "GET",
            "path": "/v1/browser/adapter/contract",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the browser adapter contract, required controls, and conformance profile."
        },
        {
            "id": "projects_browser_adapters_claim_launch",
            "upstream_operation_id": "projects.browserAdapters.claimLaunch",
            "method": "POST",
            "path": "/v1/browser/adapter/launch/claim",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "launch_request"
            ],
            "forbidden_body": [],
            "required_body": [
                "launch_request"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/browser/adapter/launch/claim."
        },
        {
            "id": "projects_browser_adapters_plan_launch",
            "upstream_operation_id": "projects.browserAdapters.planLaunch",
            "method": "POST",
            "path": "/v1/browser/adapter/launch/plan",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "admission",
                "manifest",
                "same_user_capability"
            ],
            "forbidden_body": [],
            "required_body": [
                "same_user_capability",
                "admission",
                "manifest"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/browser/adapter/launch/plan."
        },
        {
            "id": "projects_browser_adapters_register",
            "upstream_operation_id": "projects.browserAdapters.register",
            "method": "POST",
            "path": "/v1/browser/adapter/register",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "actor",
                "manifest",
                "same_user_capability",
                "sensitivity"
            ],
            "forbidden_body": [],
            "required_body": [
                "actor",
                "sensitivity",
                "same_user_capability",
                "manifest"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/browser/adapter/register."
        },
        {
            "id": "projects_browser_adapters_validate",
            "upstream_operation_id": "projects.browserAdapters.validate",
            "method": "POST",
            "path": "/v1/browser/adapter/validate",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "adapter_id",
                "contract_version",
                "launch_endpoint",
                "supported_levels",
                "supported_controls",
                "guard_fields",
                "completion_proofs"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/browser/adapter/validate."
        },
        {
            "id": "admit_browser_session",
            "upstream_operation_id": "projects.browserSessions.admit",
            "method": "POST",
            "path": "/v1/browser/admit",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "requested_level",
                "actor",
                "sensitivity"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Request admission for a browser session at a sandbox level and receive the guard plan."
        },
        {
            "id": "get_browser_profiles",
            "upstream_operation_id": "projects.browserProfiles.get",
            "method": "GET",
            "path": "/v1/browser/profiles",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the browser sandbox profile levels and suppression modes this daemon offers."
        },
        {
            "id": "get_capabilities",
            "upstream_operation_id": "projects.capabilities.get",
            "method": "GET",
            "path": "/v1/capabilities",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the sandbox capability matrix: lanes, engines, limits, and integrations."
        },
        {
            "id": "execute",
            "upstream_operation_id": "projects.executions.execute",
            "method": "POST",
            "path": "/v1/execute",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "lane",
                "source"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Execute source synchronously in a sandbox lane and return the result with metrics."
        },
        {
            "id": "health",
            "upstream_operation_id": "health",
            "method": "GET",
            "path": "/v1/health",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check sandbox-daemon liveness; returns status, version, and uptime."
        },
        {
            "id": "get_integration_contract",
            "upstream_operation_id": "projects.integration.get",
            "method": "GET",
            "path": "/v1/integration",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch the ecosystem integration contract this daemon implements."
        },
        {
            "id": "create_job",
            "upstream_operation_id": "projects.jobs.create",
            "method": "POST",
            "path": "/v1/jobs",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "lane",
                "source"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Submit an asynchronous sandbox job; returns an operation handle to poll."
        },
        {
            "id": "get_job",
            "upstream_operation_id": "projects.jobs.get",
            "method": "GET",
            "path": "/v1/jobs/{id}",
            "auth": "product",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch a sandbox job's status and result."
        },
        {
            "id": "cancel_job",
            "upstream_operation_id": "projects.jobs.cancel",
            "method": "DELETE",
            "path": "/v1/jobs/{id}",
            "auth": "product",
            "path_params": [
                "id"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Cancel a queued or running sandbox job (idempotent for already-cancelled jobs)."
        },
        {
            "id": "projects_modules_create",
            "upstream_operation_id": "projects.modules.create",
            "method": "POST",
            "path": "/v1/projects/{project}/modules",
            "auth": "product",
            "path_params": [
                "project"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [
                "bytes_base64"
            ],
            "forbidden_body": [],
            "required_body": [
                "bytes_base64"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Call POST /v1/projects/{project}/modules."
        },
        {
            "id": "projects_modules_get",
            "upstream_operation_id": "projects.modules.get",
            "method": "GET",
            "path": "/v1/projects/{project}/modules/{sha256}",
            "auth": "product",
            "path_params": [
                "project",
                "sha256"
            ],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Call GET /v1/projects/{project}/modules/{sha256}."
        }
    ],
    "remi": [
        {
            "id": "livez",
            "upstream_operation_id": "livez",
            "method": "GET",
            "path": "/livez",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check memory-server liveness."
        },
        {
            "id": "readyz",
            "upstream_operation_id": "readyz",
            "method": "GET",
            "path": "/readyz",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check memory-server readiness, including database health."
        },
        {
            "id": "health",
            "upstream_operation_id": "health",
            "method": "GET",
            "path": "/v1/health",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch deep store health: schema version, integrity checks, and graph consistency."
        },
        {
            "id": "get_stats",
            "upstream_operation_id": "getStats",
            "method": "GET",
            "path": "/v1/stats",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch memory-store statistics: ledger events, nodes, and token counts by kind."
        },
        {
            "id": "get_metrics",
            "upstream_operation_id": "getMetrics",
            "method": "GET",
            "path": "/v1/metrics",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch service metrics as JSON, including per-route counters and query-tier latencies."
        },
        {
            "id": "get_prometheus_metrics",
            "upstream_operation_id": "getPrometheusMetrics",
            "method": "GET",
            "path": "/v1/metrics/prometheus",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Fetch service metrics in Prometheus text exposition format for scrape-based monitoring."
        },
        {
            "id": "list_audit",
            "upstream_operation_id": "listAudit",
            "method": "GET",
            "path": "/v1/audit",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "List recent service audit events (default 100, maximum 500)."
        },
        {
            "id": "remember",
            "upstream_operation_id": "remember",
            "method": "POST",
            "path": "/v1/remember",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "tenant_id",
                "project_id",
                "kind",
                "text"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Write one memory event into the tenant and project ledger."
        },
        {
            "id": "project",
            "upstream_operation_id": "project",
            "method": "POST",
            "path": "/v1/project",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "limit"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Project pending ledger events into the memory graph and return the projection report."
        },
        {
            "id": "query",
            "upstream_operation_id": "query",
            "method": "POST",
            "path": "/v1/query",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
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
            "forbidden_body": [],
            "required_body": [
                "question",
                "scope"
            ],
            "body_defaults": {},
            "scope": None,
            "description": "Answer a scoped memory question with evidence and reconstruction metadata."
        },
        {
            "id": "maintenance",
            "upstream_operation_id": "maintenance",
            "method": "POST",
            "path": "/v1/maintenance",
            "auth": "product",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [
                "vacuum",
                "repair_orphans",
                "prune_audit_before_unix_ms",
                "retain_latest_audit_events"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Run store maintenance: optimize, checkpoint, and optionally vacuum, repair orphans, and prune audit history."
        }
    ],
    "dataEngine": [
        {
            "id": "health",
            "upstream_operation_id": "health.get",
            "method": "GET",
            "path": "/v1/health",
            "auth": "none",
            "path_params": [],
            "path_param_templates": {},
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": None,
            "description": "Check data-engine liveness; returns the service status."
        },
        {
            "id": "list_use_cases",
            "upstream_operation_id": "projects.useCases.list",
            "method": "GET",
            "path": "/v1/{parent}/use-cases",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List the MVP use-case templates (data products and pipeline templates) for a project."
        },
        {
            "id": "get_use_case",
            "upstream_operation_id": "projects.useCases.get",
            "method": "GET",
            "path": "/v1/{parent}/use-cases/{useCaseId}",
            "auth": "product",
            "path_params": [
                "parent",
                "useCaseId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one MVP use-case template with its rubric, modalities, skill tags, and target accuracy."
        },
        {
            "id": "ingest_artifact",
            "upstream_operation_id": "projects.artifacts.ingest",
            "method": "POST",
            "path": "/v1/{parent}/artifacts:ingest",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "artifactType",
                "source",
                "external_id",
                "raw_body",
                "metadata"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Ingest one artifact deterministically into the project; returns an async operation handle."
        },
        {
            "id": "ingest_web",
            "upstream_operation_id": "projects.web.ingest",
            "method": "POST",
            "path": "/v1/{parent}/web:ingest",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "url",
                "artifactType",
                "timeoutSeconds",
                "maxBytes",
                "producer_version",
                "metadata"
            ],
            "forbidden_body": [],
            "required_body": [
                "url"
            ],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Fetch, parse, and ingest one public HTTP(S) page as a web artifact; returns an async operation handle."
        },
        {
            "id": "create_campaign",
            "upstream_operation_id": "projects.campaigns.create",
            "method": "POST",
            "path": "/v1/{parent}/campaigns",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "task_family",
                "target_accuracy",
                "budget_cents",
                "rubric",
                "skill_tags",
                "required_reviews",
                "qualification_policy",
                "routing_policy",
                "annotation_schema",
                "idempotency_key"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Create a data campaign with a rubric, budget, target accuracy, and skill tags."
        },
        {
            "id": "list_campaigns",
            "upstream_operation_id": "projects.campaigns.list",
            "method": "GET",
            "path": "/v1/{parent}/campaigns",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List a project's data campaigns with pagination."
        },
        {
            "id": "transition_campaign",
            "upstream_operation_id": "projects.campaigns.transition",
            "method": "POST",
            "path": "/v1/{parent}/campaigns/{campaignId}:transition",
            "auth": "product",
            "path_params": [
                "parent",
                "campaignId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "target_status",
                "idempotency_key"
            ],
            "forbidden_body": [],
            "required_body": [
                "target_status",
                "idempotency_key"
            ],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Pause, resume, or permanently close campaign job admission; returns an immutable receipt for the committed lifecycle transition."
        },
        {
            "id": "get_reviewer_qualification",
            "upstream_operation_id": "projects.reviewerQualifications.get",
            "method": "GET",
            "path": "/v1/{parent}/campaigns/{campaignId}/reviewer-qualification",
            "auth": "product",
            "path_params": [
                "parent",
                "campaignId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "review:resolve",
            "description": "Fetch the authenticated reviewer's project-scoped qualification and campaign eligibility without blind-probe outcomes."
        },
        {
            "id": "run_use_case",
            "upstream_operation_id": "projects.pipelines.runUseCase",
            "method": "POST",
            "path": "/v1/{parent}/pipelines:runUseCase",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "use_case",
                "verifier",
                "budget_cents",
                "target_accuracy",
                "rubric",
                "skill_tags",
                "required_reviews",
                "urls",
                "artifacts"
            ],
            "forbidden_body": [],
            "required_body": [
                "use_case"
            ],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Run a complete MVP use-case pipeline end to end; verifier selects the configured verification backend."
        },
        {
            "id": "list_expert_tasks",
            "upstream_operation_id": "projects.expertTasks.list",
            "method": "GET",
            "path": "/v1/{parent}/expert-tasks",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "pageSize",
                "pageToken",
                "status",
                "campaignName"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List human residual review tasks, optionally filtered by status and campaign."
        },
        {
            "id": "create_review_qualification_task",
            "upstream_operation_id": "projects.reviewQualificationTasks.create",
            "method": "POST",
            "path": "/v1/{parent}/review-qualification-tasks",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "source_expert_task_name",
                "expected_label",
                "mode",
                "feedback_policy",
                "idempotency_key"
            ],
            "forbidden_body": [],
            "required_body": [
                "source_expert_task_name",
                "expected_label",
                "idempotency_key"
            ],
            "body_defaults": {},
            "scope": "review:gold:manage",
            "description": "Clone a review task into an isolated, HMAC-scored qualification task without returning the expected label."
        },
        {
            "id": "resolve_expert_task",
            "upstream_operation_id": "projects.expertTasks.resolve",
            "method": "POST",
            "path": "/v1/{parent}/expert-tasks/{expertTaskId}:resolve",
            "auth": "product",
            "path_params": [
                "parent",
                "expertTaskId"
            ],
            "path_param_templates": {
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
                "annotator_id",
                "idempotency_key",
                "lease_token",
                "review_context"
            ],
            "forbidden_body": [],
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
            "id": "claim_expert_task",
            "upstream_operation_id": "projects.expertTaskAssignments.claim",
            "method": "POST",
            "path": "/v1/{parent}/expert-tasks/{expertTaskId}:claim",
            "auth": "product",
            "path_params": [
                "parent",
                "expertTaskId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "idempotency_key",
                "lease_token",
                "lease_duration_seconds"
            ],
            "forbidden_body": [],
            "required_body": [
                "idempotency_key",
                "lease_token"
            ],
            "body_defaults": {},
            "scope": "review:resolve",
            "description": "Atomically claim one open expert task with an exclusive renewable lease."
        },
        {
            "id": "renew_expert_task_assignment",
            "upstream_operation_id": "projects.expertTaskAssignments.renew",
            "method": "POST",
            "path": "/v1/{parent}/expert-tasks/{expertTaskId}:renew",
            "auth": "product",
            "path_params": [
                "parent",
                "expertTaskId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "idempotency_key",
                "lease_token",
                "lease_duration_seconds"
            ],
            "forbidden_body": [],
            "required_body": [
                "idempotency_key",
                "lease_token"
            ],
            "body_defaults": {},
            "scope": "review:resolve",
            "description": "Renew the authenticated reviewer's active expert-task lease."
        },
        {
            "id": "release_expert_task_assignment",
            "upstream_operation_id": "projects.expertTaskAssignments.release",
            "method": "POST",
            "path": "/v1/{parent}/expert-tasks/{expertTaskId}:release",
            "auth": "product",
            "path_params": [
                "parent",
                "expertTaskId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "idempotency_key",
                "lease_token"
            ],
            "forbidden_body": [],
            "required_body": [
                "idempotency_key",
                "lease_token"
            ],
            "body_defaults": {},
            "scope": "review:resolve",
            "description": "Release the authenticated reviewer's active expert-task lease for reassignment."
        },
        {
            "id": "save_expert_task_draft",
            "upstream_operation_id": "projects.expertTaskAssignments.saveDraft",
            "method": "POST",
            "path": "/v1/{parent}/expert-tasks/{expertTaskId}:saveDraft",
            "auth": "product",
            "path_params": [
                "parent",
                "expertTaskId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "idempotency_key",
                "lease_token",
                "draft",
                "expected_version"
            ],
            "forbidden_body": [],
            "required_body": [
                "idempotency_key",
                "lease_token",
                "draft",
                "expected_version"
            ],
            "body_defaults": {},
            "scope": "review:resolve",
            "description": "Autosave a version-checked draft under the active reviewer lease."
        },
        {
            "id": "get_review_operations",
            "upstream_operation_id": "projects.reviewOperations.get",
            "method": "GET",
            "path": "/v1/{parent}/review-operations",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "windowSeconds",
                "slaTargetSeconds"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "review:resolve",
            "description": "Fetch bounded project review-operations, SLA, agreement, calibration, rubric-drift, and budget observations."
        },
        {
            "id": "get_metrics",
            "upstream_operation_id": "projects.metrics.get",
            "method": "GET",
            "path": "/v1/{parent}/metrics",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch data-engine usage and quality metrics for a project."
        },
        {
            "id": "get_label_quality",
            "upstream_operation_id": "projects.labelQuality.get",
            "method": "GET",
            "path": "/v1/{parent}/label-quality",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch the project label-quality report and unresolved expert backlog."
        },
        {
            "id": "get_ecosystem_readiness",
            "upstream_operation_id": "projects.ecosystem.readiness.get",
            "method": "GET",
            "path": "/v1/{parent}/ecosystem/readiness",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch public-site and ecosystem readiness signals for a project."
        },
        {
            "id": "list_artifacts",
            "upstream_operation_id": "projects.artifacts.list",
            "method": "GET",
            "path": "/v1/{parent}/artifacts",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "pageSize",
                "pageToken",
                "view"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List a project's artifacts with cursor pagination, expanded to the requested view (BASIC or FULL)."
        },
        {
            "id": "get_artifact",
            "upstream_operation_id": "projects.artifacts.get",
            "method": "GET",
            "path": "/v1/{parent}/artifacts/{artifactId}",
            "auth": "product",
            "path_params": [
                "parent",
                "artifactId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "view"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one artifact, expanded to the requested view (BASIC or FULL)."
        },
        {
            "id": "list_artifact_labels",
            "upstream_operation_id": "projects.artifacts.labels.list",
            "method": "GET",
            "path": "/v1/{parent}/artifacts/{artifactId}/labels",
            "auth": "product",
            "path_params": [
                "parent",
                "artifactId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List the labels attached to one artifact."
        },
        {
            "id": "profile_dataset",
            "upstream_operation_id": "projects.datasets.profile",
            "method": "POST",
            "path": "/v1/{parent}/datasets:profile",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "artifact_ids",
                "artifact_type"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Profile dataset quality before export, including duplicates, label coverage, and distributions."
        },
        {
            "id": "create_job",
            "upstream_operation_id": "projects.jobs.create",
            "method": "POST",
            "path": "/v1/{parent}/jobs",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "artifact_ids",
                "task_family",
                "campaign",
                "target_accuracy",
                "idempotency_key",
                "verifier"
            ],
            "forbidden_body": [],
            "required_body": [
                "artifact_ids",
                "task_family"
            ],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Create an asynchronous labeling job over a set of artifacts; returns an operation handle to poll."
        },
        {
            "id": "get_job",
            "upstream_operation_id": "projects.jobs.get",
            "method": "GET",
            "path": "/v1/{parent}/jobs/{jobId}",
            "auth": "product",
            "path_params": [
                "parent",
                "jobId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one labeling job with its state and progress."
        },
        {
            "id": "get_job_results",
            "upstream_operation_id": "projects.jobs.results.list",
            "method": "GET",
            "path": "/v1/{parent}/jobs/{jobId}/results",
            "auth": "product",
            "path_params": [
                "parent",
                "jobId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List the deterministic label results a job produced."
        },
        {
            "id": "get_product",
            "upstream_operation_id": "projects.products.get",
            "method": "GET",
            "path": "/v1/{parent}/products/{productId}",
            "auth": "product",
            "path_params": [
                "parent",
                "productId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one emitted product bundle with its status and manifest URL."
        },
        {
            "id": "validate_product",
            "upstream_operation_id": "projects.products.validate",
            "method": "POST",
            "path": "/v1/{parent}/products/{productId}:validate",
            "auth": "product",
            "path_params": [
                "parent",
                "productId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Validate an emitted product bundle's referential integrity and hygiene."
        },
        {
            "id": "check_product_leakage",
            "upstream_operation_id": "projects.products.checkLeakage",
            "method": "POST",
            "path": "/v1/{parent}/products:checkLeakage",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "product_ids"
            ],
            "forbidden_body": [],
            "required_body": [
                "product_ids"
            ],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Check raw-hash leakage between exactly two product bundles."
        },
        {
            "id": "get_product_manifest",
            "upstream_operation_id": "projects.products.manifest.get",
            "method": "GET",
            "path": "/v1/{parent}/products/{productId}/manifest",
            "auth": "product",
            "path_params": [
                "parent",
                "productId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch an integrity-checked, bounded manifest for an emitted eval product."
        },
        {
            "id": "admit_training_release",
            "upstream_operation_id": "projects.trainingReleases.admit",
            "method": "POST",
            "path": "/v1/{parent}/training-releases:admit",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "training_product_id",
                "heldout_product_id",
                "idempotency_key"
            ],
            "forbidden_body": [],
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
            "upstream_operation_id": "projects.trainingReleases.get",
            "method": "GET",
            "path": "/v1/{parent}/training-releases/{releaseId}",
            "auth": "product",
            "path_params": [
                "parent",
                "releaseId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "training:publish",
            "description": "Revalidate and fetch one training release, including any durable stale state."
        },
        {
            "id": "derive_bundle",
            "upstream_operation_id": "projects.products.derive",
            "method": "POST",
            "path": "/v1/{parent}/products/{productId}:derive",
            "auth": "product",
            "path_params": [
                "parent",
                "productId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "format",
                "train_fraction",
                "include_raw",
                "page_size",
                "page_token",
                "pair_sources"
            ],
            "forbidden_body": [],
            "required_body": [
                "format"
            ],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Derive a deterministic post-training bundle from a ready product."
        },
        {
            "id": "emit_eval",
            "upstream_operation_id": "projects.products.emitEval",
            "method": "POST",
            "path": "/v1/{parent}/products:emitEval",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "artifact_ids",
                "job"
            ],
            "forbidden_body": [],
            "required_body": [
                "artifact_ids",
                "job"
            ],
            "body_defaults": {},
            "scope": "eval:run",
            "description": "Emit an eval dataset bundle from verified artifacts; returns an async operation handle."
        },
        {
            "id": "extract_source",
            "upstream_operation_id": "projects.sources.extract",
            "method": "POST",
            "path": "/v1/{parent}/sources:extract",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
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
            "forbidden_body": [],
            "required_body": [
                "connector"
            ],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Extract bounded objects or records from a configured source connector."
        },
        {
            "id": "list_connectors",
            "upstream_operation_id": "projects.connectors.list",
            "method": "GET",
            "path": "/v1/{parent}/connectors",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List registered source connectors for a project."
        },
        {
            "id": "create_tool",
            "upstream_operation_id": "projects.tools.create",
            "method": "POST",
            "path": "/v1/{parent}/tools",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "name",
                "description",
                "input_schema",
                "kind",
                "implementation",
                "created_by"
            ],
            "forbidden_body": [],
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
            "upstream_operation_id": "projects.tools.list",
            "method": "GET",
            "path": "/v1/{parent}/tools",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List stored custom tools and their usage statistics."
        },
        {
            "id": "get_tool",
            "upstream_operation_id": "projects.tools.get",
            "method": "GET",
            "path": "/v1/{parent}/tools/{toolName}",
            "auth": "product",
            "path_params": [
                "parent",
                "toolName"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one stored custom tool and its usage statistics."
        },
        {
            "id": "delete_tool",
            "upstream_operation_id": "projects.tools.delete",
            "method": "DELETE",
            "path": "/v1/{parent}/tools/{toolName}",
            "auth": "product",
            "path_params": [
                "parent",
                "toolName"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Delete a stored custom tool and every retained version."
        },
        {
            "id": "invoke_tool",
            "upstream_operation_id": "projects.tools.invoke",
            "method": "POST",
            "path": "/v1/{parent}/tools/{toolName}:invoke",
            "auth": "product",
            "path_params": [
                "parent",
                "toolName"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [
                "arguments"
            ],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:write",
            "description": "Invoke a stored custom tool through its configured execution boundary."
        },
        {
            "id": "create_evidence_record",
            "upstream_operation_id": "projects.evidenceRecords.create",
            "method": "POST",
            "path": "/v1/{parent}/evidenceRecords",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
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
            "forbidden_body": [],
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
            "upstream_operation_id": "projects.evidenceRecords.list",
            "method": "GET",
            "path": "/v1/{parent}/evidenceRecords",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "pageSize",
                "pageToken",
                "domain"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List immutable shared evidence records with bounded cursor pagination."
        },
        {
            "id": "get_evidence_record",
            "upstream_operation_id": "projects.evidenceRecords.get",
            "method": "GET",
            "path": "/v1/{parent}/evidenceRecords/{evidenceRecordId}",
            "auth": "product",
            "path_params": [
                "parent",
                "evidenceRecordId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one immutable shared evidence record by its platform digest."
        },
        {
            "id": "create_episode",
            "upstream_operation_id": "projects.episodes.create",
            "method": "POST",
            "path": "/v1/{parent}/episodes",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
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
            "forbidden_body": [],
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
            "upstream_operation_id": "projects.episodes.list",
            "method": "GET",
            "path": "/v1/{parent}/episodes",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "pageSize",
                "pageToken",
                "domain"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List immutable shared episodes with bounded cursor pagination."
        },
        {
            "id": "get_episode",
            "upstream_operation_id": "projects.episodes.get",
            "method": "GET",
            "path": "/v1/{parent}/episodes/{episodeId}",
            "auth": "product",
            "path_params": [
                "parent",
                "episodeId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one immutable shared episode by its platform digest."
        },
        {
            "id": "query_research_retrieval",
            "upstream_operation_id": "query_research_retrieval",
            "method": "POST",
            "path": "/v1/{parent}/researchRetrieval:query",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
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
            "forbidden_body": [],
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
            "upstream_operation_id": "projects.researchCatalogEntries.create",
            "method": "POST",
            "path": "/v1/{parent}/researchCatalogEntries",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
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
            "forbidden_body": [],
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
            "upstream_operation_id": "projects.researchCatalogEntries.list",
            "method": "GET",
            "path": "/v1/{parent}/researchCatalogEntries",
            "auth": "product",
            "path_params": [
                "parent"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [
                "pageSize",
                "pageToken"
            ],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "List immutable executable research catalog entries with bounded pagination."
        },
        {
            "id": "get_research_catalog_entry",
            "upstream_operation_id": "projects.researchCatalogEntries.get",
            "method": "GET",
            "path": "/v1/{parent}/researchCatalogEntries/{entryId}",
            "auth": "product",
            "path_params": [
                "parent",
                "entryId"
            ],
            "path_param_templates": {
                "parent": "projects/*"
            },
            "query": [],
            "body": [],
            "forbidden_body": [],
            "required_body": [],
            "body_defaults": {},
            "scope": "dataset:read",
            "description": "Fetch one immutable executable research catalog entry by content hash."
        }
    ]
}

MCP_GATEWAY = {
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
            "id": "list_tools",
            "rpc": "tools/list",
            "description": "List the fixed ten-verb Tempera capability-fabric surface; product cards never appear as flat product tool names."
        },
        {
            "id": "call_tool",
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
