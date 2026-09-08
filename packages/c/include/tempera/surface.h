/* GENERATED FROM surface.json by scripts/gen-sdk-surface.py -- DO NOT EDIT BY HAND. */
/* The SDK surface tables: products, audiences, scopes, environments, */
/* the error contract, and every typed operation, shared verbatim with */
/* the TypeScript, Python, Rust, and C++ packages. */

#ifndef TEMPERA_SURFACE_H
#define TEMPERA_SURFACE_H

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* surface.json manifest revision these tables were generated from. */
#define TEMPERA_SURFACE_VERSION 6

/* One (key, value) entry of a generated string table. */
typedef struct tempera_str_pair {
    const char *key;
    const char *value;
} tempera_str_pair;

/* Registered token audiences; TEMPERA_AUDIENCE_COUNT entries. */
extern const char *const TEMPERA_AUDIENCES[];
extern const size_t TEMPERA_AUDIENCE_COUNT;
extern const char *const TEMPERA_DEFAULT_AUDIENCE;

/* Registered OAuth scopes; TEMPERA_SCOPE_COUNT entries. */
extern const char *const TEMPERA_SCOPES[];
extern const size_t TEMPERA_SCOPE_COUNT;

/* Issuer paths, relative to the control-plane issuer URL. */
extern const char *const TEMPERA_AUTHORIZE_PATH;
extern const char *const TEMPERA_TOKEN_PATH;
extern const char *const TEMPERA_REVOKE_PATH;
extern const char *const TEMPERA_INTROSPECT_PATH;
extern const char *const TEMPERA_MCP_PATH;

/* One environment preset. */
typedef struct tempera_environment_target {
    const char *environment;
    const char *auth_issuer_url;
    const char *auth_jwks_url;
    const char *control_plane_url;
    const char *cradle_api_url;
    const char *data_engine_api_url;
    const char *mcp_gateway_url;
    const char *palette_api_url;
    const char *palette_mcp_url;
    const char *public_site_url;
    const char *tempera_gym_url;
    const char *tempera_llm_api_url;
    const char *tempera_risk_api_url;
    const char *tempera_workflows_api_url;
    const char *tempo_api_url;
} tempera_environment_target;

extern const tempera_environment_target TEMPERA_ENVIRONMENTS[];
extern const size_t TEMPERA_ENVIRONMENT_COUNT;

/* One product in the registry. */
typedef struct tempera_product_spec {
    const char *key;
    const char *name;
    const char *repository;
    const char *env_var;
    /* NULL when the product has no pinned token audience. */
    const char *audience;
    const char *description;
} tempera_product_spec;

extern const tempera_product_spec TEMPERA_PRODUCTS[];
extern const size_t TEMPERA_PRODUCT_COUNT;

/* One typed operation. Array members are NULL when the count is 0. */
typedef struct tempera_operation_spec {
    const char *product;
    const char *id;
    const char *upstream_operation_id;
    const char *method;
    const char *path;
    const char *auth;
    /* NULL unless auth is "oauthResource". */
    const char *auth_audience;
    const char *const *path_params;
    size_t path_param_count;
    const tempera_str_pair *path_param_templates;
    size_t path_param_template_count;
    const char *const *query;
    size_t query_count;
    const char *const *required_query;
    size_t required_query_count;
    const char *const *headers;
    size_t header_count;
    const char *const *required_headers;
    size_t required_header_count;
    const char *const *body;
    size_t body_count;
    const char *const *forbidden_body;
    size_t forbidden_body_count;
    const char *const *required_body;
    size_t required_body_count;
    const tempera_str_pair *body_defaults;
    size_t body_default_count;
    const char *request_body_kind;
    /* NULL unless request_body_kind is "binary". */
    const char *request_content_type;
    /* NULL when the operation requires no scope. */
    const char *scope;
    bool physical_action;
    bool prepare_commit_required;
    const char *safe_retry;
    const char *description;
} tempera_operation_spec;

/* Every operation of every product, flat, carrying its product key. */
extern const tempera_operation_spec TEMPERA_OPERATIONS[];
extern const size_t TEMPERA_OPERATION_COUNT;

/* One JSON-RPC method of the unified MCP gateway. */
typedef struct tempera_mcp_method_spec {
    const char *id;
    const char *rpc;
    /* NULL when the method is not a tool call. */
    const char *tool;
    const char *description;
} tempera_mcp_method_spec;

extern const tempera_mcp_method_spec TEMPERA_MCP_METHODS[];
extern const size_t TEMPERA_MCP_METHOD_COUNT;

/* MCP gateway JSON-RPC error codes. */
#define TEMPERA_MCP_ERROR_PLAN_LIMIT (-32002)
#define TEMPERA_MCP_ERROR_INVALID_REQUEST (-32600)
#define TEMPERA_MCP_ERROR_METHOD_NOT_FOUND (-32601)
#define TEMPERA_MCP_ERROR_INVALID_PARAMS (-32602)
#define TEMPERA_MCP_ERROR_INTERNAL (-32603)

/* Look up one operation by product key and snake_case operation id. */
const tempera_operation_spec *tempera_find_operation(const char *product,
                                                    const char *id);

/* Look up one product by snake_case key. */
const tempera_product_spec *tempera_find_product(const char *key);

#ifdef __cplusplus
}
#endif

#endif /* TEMPERA_SURFACE_H */
