/*
 * Dependency-free Tempera SDK for C (C99).
 *
 * The library is HTTP-less by design, exactly like packages/rust: it builds
 * request URLs, query pairs, headers, and bodies for the caller's own HTTP
 * client instead of sending them. Every product, audience, scope, environment
 * target, and typed operation comes from the generated tables in
 * <tempera/surface.h> (rendered from surface.json), shared verbatim with the
 * TypeScript, Python, Rust, and C++ packages.
 *
 *   surface.h  the generated tables. GENERATED -- never edit by hand.
 *   tempera.h  this file: the hand-written runtime.
 *
 * ---------------------------------------------------------------------------
 * MEMORY OWNERSHIP CONTRACT
 * ---------------------------------------------------------------------------
 * 1. Every pointer the caller passes in (const char *, tempera_param arrays,
 *    byte buffers) is BORROWED for the duration of the call only. The library
 *    copies whatever it needs to retain. The single exception is
 *    tempera_client_set_auth(), which stores the borrowed tempera_auth pointer:
 *    that auth object must outlive the client (it is documented again there).
 * 2. Every char * returned by a tempera_* function is heap-allocated and owned
 *    by the caller; release it with tempera_string_free().
 * 3. Every struct with owned members has a matching tempera_<type>_free():
 *    tempera_request_free(), tempera_api_error_free(), tempera_mcp_error_free(),
 *    tempera_pkce_pair_free(). They release the members and, for the two opaque
 *    handles (tempera_client, tempera_auth), the handle itself.
 * 4. Every _free() accepts NULL and is a no-op then, and leaves freed structs
 *    zeroed so a double free is a no-op too.
 * 5. Pointers returned as const char * from a getter (for example
 *    tempera_auth_bearer_for()) are BORROWED from the object and stay valid
 *    until that object is mutated or freed. Never pass one to
 *    tempera_string_free().
 * 6. Pointers into the generated tables (tempera_operation_spec *,
 *    tempera_product_spec *) have static storage duration and are never freed.
 * 7. The library keeps no global mutable state: nothing is cached between
 *    calls, getenv() results are copied immediately, and every handle is
 *    explicitly created and destroyed by the caller.
 */

#ifndef TEMPERA_TEMPERA_H
#define TEMPERA_TEMPERA_H

#include <stdbool.h>
#include <stddef.h>

#include "tempera/surface.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Package version; identical across every Tempera SDK language package. */
#define TEMPERA_SDK_VERSION "0.12.0"

/* MCP protocol revision sent in initialize requests. */
#define TEMPERA_MCP_PROTOCOL_VERSION "2025-06-18"

/* Maximum wire length of an idempotency key, in bytes. */
#define TEMPERA_MAX_IDEMPOTENCY_KEY_BYTES 256

/* Bytes of human-readable context carried by tempera_error. */
#define TEMPERA_ERROR_DETAIL_MAX 512

/*
 * Every way a request can fail before it exists. These mirror the Rust
 * BuildError variants one-for-one.
 */
typedef enum tempera_status {
    TEMPERA_OK = 0,
    /* No operation with this product key and operation id exists. */
    TEMPERA_ERR_UNKNOWN_OPERATION,
    /* A {placeholder} in the operation path had no matching parameter. */
    TEMPERA_ERR_MISSING_PATH_PARAM,
    /* A producer-required query parameter was absent or empty. */
    TEMPERA_ERR_MISSING_QUERY_PARAM,
    /* A path parameter did not match its declared AIP resource pattern. */
    TEMPERA_ERR_INVALID_PATH_PARAM,
    /* A field the producer derives from the principal was supplied. */
    TEMPERA_ERR_FORBIDDEN_BODY_FIELD,
    /* Both a canonical wire name and its snake_case alias were supplied. */
    TEMPERA_ERR_DUPLICATE_PARAMETER_ALIAS,
    /* An idempotency key was not exact ASCII-graphic bytes within bounds. */
    TEMPERA_ERR_INVALID_IDEMPOTENCY_KEY,
    /* The operation needs an account-session token and none is configured. */
    TEMPERA_ERR_MISSING_ACCOUNT_TOKEN,
    /* The operation needs the introspection secret and none is configured. */
    TEMPERA_ERR_MISSING_INTROSPECTION_SECRET,
    /* No credential resolves for the operation's token audience. */
    TEMPERA_ERR_MISSING_CREDENTIAL,
    /* A generated operation is missing required static contract metadata. */
    TEMPERA_ERR_INVALID_OPERATION_CONTRACT,
    /* No base URL is configured for the product and its env var is unset. */
    TEMPERA_ERR_MISSING_BASE_URL,
    /* An allocation failed. */
    TEMPERA_ERR_OUT_OF_MEMORY,
    /* A required argument was NULL or otherwise unusable. */
    TEMPERA_ERR_INVALID_ARGUMENT
} tempera_status;

/*
 * Stable one-line description of a status code. The returned pointer is a
 * string literal with static storage duration; never free it.
 */
const char *tempera_error_message(tempera_status status);

/*
 * Failure detail. `detail` is a NUL-terminated, self-contained message such as
 * "palette.get_trace: missing required path parameter \"traceId\"". No
 * allocation is involved, so a tempera_error never needs freeing.
 */
typedef struct tempera_error {
    tempera_status status;
    char detail[TEMPERA_ERROR_DETAIL_MAX];
} tempera_error;

/* ------------------------------------------------------------------------ */
/* Parameters                                                                */
/* ------------------------------------------------------------------------ */

typedef enum tempera_param_kind {
    /* JSON string in bodies, plain text in paths and query strings. */
    TEMPERA_PARAM_STRING = 0,
    /* JSON number literal in bodies. */
    TEMPERA_PARAM_INT,
    /* JSON true/false literal in bodies. */
    TEMPERA_PARAM_BOOL,
    /* Pre-serialized JSON spliced verbatim (objects, arrays, floats, null). */
    TEMPERA_PARAM_RAW_JSON
} tempera_param_kind;

/*
 * One request parameter. `name` and `string_value` are borrowed for the
 * duration of the build call; nothing here is owned.
 */
typedef struct tempera_param {
    const char *name;
    tempera_param_kind kind;
    const char *string_value;
    long long int_value;
    bool bool_value;
} tempera_param;

tempera_param tempera_param_string(const char *name, const char *value);
tempera_param tempera_param_int(const char *name, long long value);
tempera_param tempera_param_bool(const char *name, bool value);
tempera_param tempera_param_json(const char *name, const char *raw_json);

/* ------------------------------------------------------------------------ */
/* Requests                                                                  */
/* ------------------------------------------------------------------------ */

/* One owned key/value pair of a built request. */
typedef struct tempera_kv {
    char *name;
    char *value;
} tempera_kv;

/*
 * A fully-described HTTP request for the caller's HTTP client to send.
 * Everything except `method` (a pointer into the generated tables) is owned by
 * the request; release the whole thing with tempera_request_free().
 */
typedef struct tempera_request {
    /* HTTP method, borrowed from the generated operation table. */
    const char *method;
    /* Base URL plus the substituted path, WITHOUT the query string. */
    char *url;
    /* Query parameters as unencoded key/value pairs. */
    tempera_kv *query;
    size_t query_count;
    /* accept, content-type (when a body is present), authorization. */
    tempera_kv *headers;
    size_t header_count;
    /* Serialized JSON body, or NULL when the operation carries none. */
    char *body_json;
    /* Raw binary body for upload operations, or NULL. */
    unsigned char *body_bytes;
    size_t body_bytes_len;
} tempera_request;

/* Release a request built by this library. Accepts NULL. */
void tempera_request_free(tempera_request *request);

/*
 * The complete URL: request->url plus the urlencoded query string.
 * Returns a newly allocated string (free with tempera_string_free) or NULL on
 * allocation failure.
 */
char *tempera_request_full_url(const tempera_request *request);

/* Borrowed header value for `name`, or NULL when the header is absent. */
const char *tempera_request_header(const tempera_request *request, const char *name);

/* Borrowed query value for `name`, or NULL when the parameter is absent. */
const char *tempera_request_query(const tempera_request *request, const char *name);

/* Release any char * returned by this library. Accepts NULL. */
void tempera_string_free(char *value);

/* ------------------------------------------------------------------------ */
/* Auth                                                                      */
/* ------------------------------------------------------------------------ */

/*
 * One unified credential (central tp_ API key plus per-audience OAuth tokens)
 * against one issuer. Opaque; create with tempera_auth_new(), release with
 * tempera_auth_free().
 */
typedef struct tempera_auth tempera_auth;

/*
 * Create a credential store against one issuer (for example the
 * onboarding-provisioned staging issuer URL); a trailing slash is trimmed.
 * Returns NULL on allocation failure or a NULL issuer.
 */
tempera_auth *tempera_auth_new(const char *issuer_url);
void tempera_auth_free(tempera_auth *auth);

/* Set the OAuth client id used in authorize/token/revoke requests. */
tempera_status tempera_auth_set_client_id(tempera_auth *auth, const char *client_id);
/* Set the central tp_ API key: the fallback bearer for every audience. */
tempera_status tempera_auth_set_api_key(tempera_auth *auth, const char *api_key);

/*
 * Store an /oauth/token response for one audience. Refresh-token rotation: a
 * newly issued refresh token replaces the old one; when `refresh_token` is
 * NULL the previously stored one is kept. Pass expires_in < 0 and scope NULL
 * when the response omitted them.
 */
tempera_status tempera_auth_apply_token_response(tempera_auth *auth,
                                                 const char *audience,
                                                 const char *access_token,
                                                 const char *refresh_token,
                                                 long long expires_in,
                                                 const char *scope);

/*
 * The bearer to present at a product server for `audience`: the audience's
 * access token, falling back to the unified API key. Borrowed from `auth`;
 * valid until the store is mutated or freed. NULL when nothing resolves.
 */
const char *tempera_auth_bearer_for(const tempera_auth *auth, const char *audience);

/* "Bearer <token>" for `audience`, newly allocated, or NULL when none resolves. */
char *tempera_auth_authorization_header(const tempera_auth *auth, const char *audience);

/* The issuer URL this credential targets (borrowed, no trailing slash). */
const char *tempera_auth_issuer_url(const tempera_auth *auth);

/* Newly allocated issuer endpoint URLs. */
char *tempera_auth_token_url(const tempera_auth *auth);
char *tempera_auth_revoke_url(const tempera_auth *auth);
char *tempera_auth_mcp_url(const tempera_auth *auth);

/* Inputs to tempera_auth_authorize_url(); all members are borrowed. */
typedef struct tempera_authorize_url_params {
    const char *client_id;
    const char *redirect_uri;
    /* PKCE S256 code challenge (see tempera_pkce_pair_from_entropy). */
    const char *code_challenge;
    /* Token audience, sent as the RFC 8707 `resource` parameter. */
    const char *audience;
    /* Optional space-separated scope list; may be NULL. */
    const char *scope;
    /* Optional opaque state echoed back on the redirect; may be NULL. */
    const char *state;
} tempera_authorize_url_params;

/* Authorize URL with PKCE (S256) and the RFC 8707 resource selector. */
char *tempera_auth_authorize_url(const tempera_auth *auth,
                                 const tempera_authorize_url_params *params);

/*
 * application/x-www-form-urlencoded bodies for the issuer's token endpoints.
 * The library sends nothing; POST these yourself.
 */
char *tempera_auth_code_exchange_body(const tempera_auth *auth,
                                      const char *code,
                                      const char *code_verifier,
                                      const char *redirect_uri,
                                      const char *audience);
/* NULL when no refresh token is stored for the audience. */
char *tempera_auth_refresh_body(const tempera_auth *auth, const char *audience);
/* Also drops the stored token set. NULL when the audience is unknown. */
char *tempera_auth_revoke_body(tempera_auth *auth, const char *audience);

/* Percent-encode one value (RFC 3986 unreserved set). Newly allocated. */
char *tempera_url_encode(const char *value);

/* Base64url without padding (RFC 4648 section 5). Newly allocated. */
char *tempera_base64url_no_pad(const unsigned char *data, size_t length);

/* S256 code challenge: base64url(SHA-256(verifier)), no padding. */
char *tempera_pkce_challenge_s256(const char *verifier);

/*
 * Build a PKCE code verifier from CALLER-SUPPLIED entropy: the unpadded
 * base64url encoding of the bytes (RFC 7636 section 4.1). The library is
 * dependency-free and has no RNG, so supply at least 32 cryptographically
 * random bytes from the platform CSPRNG.
 */
char *tempera_pkce_verifier_from_entropy(const unsigned char *entropy, size_t length);

/* A PKCE verifier/challenge pair; `method` is always the literal "S256". */
typedef struct tempera_pkce_pair {
    char *verifier;
    char *challenge;
    const char *method;
} tempera_pkce_pair;

/*
 * Full PKCE pair from caller-supplied entropy. On failure both strings are
 * NULL. Release with tempera_pkce_pair_free().
 */
tempera_pkce_pair tempera_pkce_pair_from_entropy(const unsigned char *entropy, size_t length);
void tempera_pkce_pair_free(tempera_pkce_pair *pair);

/* ------------------------------------------------------------------------ */
/* Client                                                                    */
/* ------------------------------------------------------------------------ */

/*
 * The unified Tempera client: one credential set, every product, no HTTP.
 * Opaque; create with tempera_client_new(), release with tempera_client_free().
 */
typedef struct tempera_client tempera_client;

tempera_client *tempera_client_new(void);
void tempera_client_free(tempera_client *client);

/*
 * Attach the unified credential used by `auth: "product"` and
 * `auth: "oauthResource"` operations. The client BORROWS `auth`: the auth
 * object must outlive the client, and the client never frees it. Pass NULL to
 * detach.
 */
tempera_status tempera_client_set_auth(tempera_client *client, const tempera_auth *auth);

/* Account-session token for control-plane (`auth: "account"`) operations. */
tempera_status tempera_client_set_account_token(tempera_client *client, const char *token);

/* Server-side secret for `auth: "introspectionSecret"` operations. */
tempera_status tempera_client_set_introspection_secret(tempera_client *client,
                                                       const char *secret);

/* Base URL for one product, overriding that product's env var. */
tempera_status tempera_client_set_base_url(tempera_client *client,
                                           const char *product,
                                           const char *url);

/*
 * Build the request for one typed operation.
 *
 * `product` is a snake_case product key and `operation` a snake_case operation
 * id from the generated tables (for example "palette", "get_trace").
 * Parameters accept canonical producer wire names or their snake_case aliases,
 * but never both for the same field. Path parameters substitute into the URL
 * (percent-encoded), declared query keys go to the query string, declared body
 * keys plus the operation's body defaults form the JSON body, and undeclared
 * extras go to the query on GET/DELETE and into the body otherwise. Emitted
 * names are always canonical producer wire names.
 *
 * The base URL is resolved as: the explicit tempera_client_set_base_url()
 * override, then the product's envVar through getenv().
 *
 * On success returns TEMPERA_OK and stores a newly allocated request in
 * *out_request (free it with tempera_request_free). On failure returns the
 * status, leaves *out_request NULL, and -- when out_error is non-NULL -- fills
 * in the status and a human-readable detail line.
 */
tempera_status tempera_client_build_request(const tempera_client *client,
                                            const char *product,
                                            const char *operation,
                                            const tempera_param *params,
                                            size_t param_count,
                                            tempera_request **out_request,
                                            tempera_error *out_error);

/*
 * Build a request from an already-resolved operation and product spec, skipping
 * the table lookup. Identical in every other respect to
 * tempera_client_build_request(); useful in a hot loop that already holds the
 * spec pointers, and the seam the test suite uses to exercise contract rules
 * (such as forbiddenBody) that no shipped operation exercises yet. `op` and
 * `product_spec` are borrowed and must have static storage duration or outlive
 * the call.
 */
tempera_status tempera_client_build_request_spec(const tempera_client *client,
                                                 const tempera_operation_spec *op,
                                                 const tempera_product_spec *product_spec,
                                                 const tempera_param *params,
                                                 size_t param_count,
                                                 tempera_request **out_request,
                                                 tempera_error *out_error);

/*
 * Build a request for a producer-declared binary upload operation. Identical
 * to tempera_client_build_request(), plus: the operation must declare
 * requestBodyKind "binary" (otherwise TEMPERA_ERR_INVALID_OPERATION_CONTRACT),
 * `content` is COPIED into the request, and the operation's
 * requestContentType is appended as a content-type header.
 */
tempera_status tempera_client_build_binary(const tempera_client *client,
                                           const char *product,
                                           const char *operation,
                                           const tempera_param *params,
                                           size_t param_count,
                                           const unsigned char *content,
                                           size_t content_length,
                                           tempera_request **out_request,
                                           tempera_error *out_error);

/* ------------------------------------------------------------------------ */
/* Errors on the wire                                                        */
/* ------------------------------------------------------------------------ */

/*
 * An HTTP error response from any Tempera product, normalized from the
 * canonical AIP-193 envelope and the supported compatibility shapes. `message`
 * is never NULL; the other strings are NULL when the wire shape carried no
 * such member. Release with tempera_api_error_free().
 */
typedef struct tempera_api_error {
    int status;
    char *code;
    char *message;
    char *reason;
    char *request_id;
} tempera_api_error;

/*
 * Normalize any product error body. `body` may be NULL, empty, or
 * unparseable, in which case `message` becomes `status_text`, or the literal
 * "request failed" when the status text is empty too. Returns TEMPERA_OK, or
 * TEMPERA_ERR_OUT_OF_MEMORY / TEMPERA_ERR_INVALID_ARGUMENT.
 */
tempera_status tempera_normalize_error_body(int status,
                                            const char *status_text,
                                            const char *body,
                                            tempera_api_error *out_error);
void tempera_api_error_free(tempera_api_error *error);

/*
 * Escape one string for inclusion inside a JSON string literal, WITHOUT the
 * surrounding quotes. Newly allocated.
 */
char *tempera_json_escape(const char *value);

/* ------------------------------------------------------------------------ */
/* MCP gateway                                                               */
/* ------------------------------------------------------------------------ */

/*
 * Builds JSON-RPC 2.0 request bodies for the unified MCP gateway with
 * monotonically increasing request ids. A plain value type: initialize it with
 * tempera_mcp_builder_init() and let it go out of scope; nothing is owned.
 */
typedef struct tempera_mcp_builder {
    long long next_id;
} tempera_mcp_builder;

/* Initialize a builder whose first request id is 1. */
void tempera_mcp_builder_init(tempera_mcp_builder *builder);

/*
 * Each body builder returns a newly allocated JSON-RPC body (free with
 * tempera_string_free) and, when out_id is non-NULL, stores the request id it
 * used so the caller can correlate the response.
 */
char *tempera_mcp_initialize_body(tempera_mcp_builder *builder,
                                  const char *client_name,
                                  const char *client_version,
                                  long long *out_id);
char *tempera_mcp_ping_body(tempera_mcp_builder *builder, long long *out_id);
char *tempera_mcp_list_tools_body(tempera_mcp_builder *builder, long long *out_id);
/*
 * `arguments_json` must be a serialized JSON object, spliced verbatim; NULL
 * sends empty arguments ({}).
 */
char *tempera_mcp_call_tool_body(tempera_mcp_builder *builder,
                                 const char *tool_name,
                                 const char *arguments_json,
                                 long long *out_id);
char *tempera_mcp_whoami_body(tempera_mcp_builder *builder, long long *out_id);
char *tempera_mcp_status_body(tempera_mcp_builder *builder, long long *out_id);

/*
 * A JSON-RPC error returned by an MCP endpoint. Gateway codes are the
 * TEMPERA_MCP_ERROR_* constants in <tempera/surface.h>.
 */
typedef struct tempera_mcp_error {
    long long code;
    char *message;
} tempera_mcp_error;

/*
 * Extract the JSON-RPC error from an MCP response body, if any. Returns true
 * and fills *out_error when the body carried one; false for success responses
 * and unparseable bodies. Release with tempera_mcp_error_free().
 */
bool tempera_mcp_parse_error(const char *body, tempera_mcp_error *out_error);
void tempera_mcp_error_free(tempera_mcp_error *error);

#ifdef __cplusplus
}
#endif

#endif /* TEMPERA_TEMPERA_H */
