/*
 * The unified Tempera client, HTTP-less: it resolves an operation from the
 * generated surface tables (<tempera/surface.h>) and builds a fully-described
 * tempera_request (method, URL, query, headers, JSON body) for the caller's own
 * HTTP client to send.
 *
 * Mirrors the Rust TemperaClient dispatch semantics exactly:
 *  - Typed operations by product key + snake_case operation id. Parameters
 *    accept canonical wire names and snake_case aliases; requests always emit
 *    the producer's canonical wire names.
 *  - Declared query keys route to the query string; declared body keys plus
 *    body defaults form the JSON body.
 *  - Forward compatibility: undeclared parameters flow to the query string on
 *    GET/DELETE and into the JSON body otherwise, so a new server field is
 *    usable before the surface tables catch up.
 *  - Auth kinds: none, account, introspectionSecret, oauthResource (an
 *    operation-pinned audience) and product (the product's audience through
 *    tempera_auth, with unified tp_ API-key fallback).
 */

#include <stdlib.h>
#include <string.h>

#include "internal.h"

/* Request-body field names that carry a client-minted idempotency key. */
static const char *const IDEMPOTENCY_KEY_FIELDS[] = {"idempotencyKey", "idempotency_key"};

typedef struct base_url_entry {
    char *product;
    char *url;
} base_url_entry;

struct tempera_client {
    /* Borrowed: the caller owns the auth object and must outlive the client. */
    const tempera_auth *auth;
    char *account_token;
    char *introspection_secret;
    base_url_entry *base_urls;
    size_t base_url_count;
};

/* ------------------------------------------------------------------------ */
/* Parameters                                                                */
/* ------------------------------------------------------------------------ */

tempera_param tempera_param_string(const char *name, const char *value)
{
    tempera_param param;

    memset(&param, 0, sizeof(param));
    param.name = name;
    param.kind = TEMPERA_PARAM_STRING;
    param.string_value = value;
    return param;
}

tempera_param tempera_param_int(const char *name, long long value)
{
    tempera_param param;

    memset(&param, 0, sizeof(param));
    param.name = name;
    param.kind = TEMPERA_PARAM_INT;
    param.int_value = value;
    return param;
}

tempera_param tempera_param_bool(const char *name, bool value)
{
    tempera_param param;

    memset(&param, 0, sizeof(param));
    param.name = name;
    param.kind = TEMPERA_PARAM_BOOL;
    param.bool_value = value;
    return param;
}

tempera_param tempera_param_json(const char *name, const char *raw_json)
{
    tempera_param param;

    memset(&param, 0, sizeof(param));
    param.name = name;
    param.kind = TEMPERA_PARAM_RAW_JSON;
    param.string_value = raw_json;
    return param;
}

/* Plain-text form, used for path substitution and query-string values. */
static char *param_plain_string(const tempera_param *param)
{
    tempera_buf buf;

    switch (param->kind) {
    case TEMPERA_PARAM_STRING:
    case TEMPERA_PARAM_RAW_JSON:
        return tempera_strdup(param->string_value != NULL ? param->string_value : "");
    case TEMPERA_PARAM_INT:
        tempera_buf_init(&buf);
        tempera_buf_append_i64(&buf, param->int_value);
        return tempera_buf_finish(&buf);
    case TEMPERA_PARAM_BOOL:
        return tempera_strdup(param->bool_value ? "true" : "false");
    }
    return NULL;
}

/* JSON form, used for body members. */
static char *param_json_fragment(const tempera_param *param)
{
    tempera_buf buf;
    char *escaped;

    switch (param->kind) {
    case TEMPERA_PARAM_STRING:
        escaped = tempera_json_escape(param->string_value != NULL ? param->string_value : "");
        if (escaped == NULL) {
            return NULL;
        }
        tempera_buf_init(&buf);
        tempera_buf_append_char(&buf, '"');
        tempera_buf_append(&buf, escaped);
        tempera_buf_append_char(&buf, '"');
        tempera_string_free(escaped);
        return tempera_buf_finish(&buf);
    case TEMPERA_PARAM_RAW_JSON:
        return tempera_strdup(param->string_value != NULL ? param->string_value : "null");
    case TEMPERA_PARAM_INT:
        tempera_buf_init(&buf);
        tempera_buf_append_i64(&buf, param->int_value);
        return tempera_buf_finish(&buf);
    case TEMPERA_PARAM_BOOL:
        return tempera_strdup(param->bool_value ? "true" : "false");
    }
    return NULL;
}

/* ------------------------------------------------------------------------ */
/* Owned key/value lists                                                     */
/* ------------------------------------------------------------------------ */

typedef struct kv_list {
    tempera_kv *items;
    size_t count;
    bool failed;
} kv_list;

static void kv_list_init(kv_list *list)
{
    list->items = NULL;
    list->count = 0;
    list->failed = false;
}

static void kv_list_dispose(kv_list *list)
{
    size_t index;

    for (index = 0; index < list->count; index++) {
        free(list->items[index].name);
        free(list->items[index].value);
    }
    free(list->items);
    kv_list_init(list);
}

/* Take ownership of both strings; frees them and latches failure on error. */
static void kv_list_push_owned(kv_list *list, char *name, char *value)
{
    tempera_kv *grown;

    if (name == NULL || value == NULL) {
        list->failed = true;
        free(name);
        free(value);
        return;
    }
    grown = (tempera_kv *)realloc(list->items, (list->count + 1) * sizeof(*grown));
    if (grown == NULL) {
        list->failed = true;
        free(name);
        free(value);
        return;
    }
    list->items = grown;
    list->items[list->count].name = name;
    list->items[list->count].value = value;
    list->count++;
}

static void kv_list_push(kv_list *list, const char *name, const char *value)
{
    kv_list_push_owned(list, tempera_strdup(name), tempera_strdup(value));
}

/* Insert or replace one member, keeping keys unique (set_body_member). */
static void kv_list_set_owned(kv_list *list, const char *name, char *value)
{
    size_t index;

    if (value == NULL) {
        list->failed = true;
        return;
    }
    for (index = 0; index < list->count; index++) {
        if (strcmp(list->items[index].name, name) == 0) {
            free(list->items[index].value);
            list->items[index].value = value;
            return;
        }
    }
    kv_list_push_owned(list, tempera_strdup(name), value);
}

/* ------------------------------------------------------------------------ */
/* Name handling                                                             */
/* ------------------------------------------------------------------------ */

static char *snake_case(const char *value)
{
    tempera_buf buf;
    size_t index;

    tempera_buf_init(&buf);
    for (index = 0; value[index] != '\0'; index++) {
        char character = value[index];

        if (character >= 'A' && character <= 'Z') {
            if (index > 0) {
                tempera_buf_append_char(&buf, '_');
            }
            tempera_buf_append_char(&buf, (char)(character - 'A' + 'a'));
        } else {
            tempera_buf_append_char(&buf, character);
        }
    }
    return tempera_buf_finish(&buf);
}

static bool string_list_contains(const char *const *values, size_t count, const char *needle)
{
    size_t index;

    for (index = 0; index < count; index++) {
        if (strcmp(values[index], needle) == 0) {
            return true;
        }
    }
    return false;
}

/*
 * Find the parameter a declared wire name refers to: the canonical name, or
 * its snake_case alias. Supplying both is an error. Returns the index through
 * *out_index, or (size_t)-1 when the parameter was not supplied.
 */
static tempera_status declared_param(const tempera_param *params,
                                     size_t param_count,
                                     const char *wire_name,
                                     size_t *out_index,
                                     char **out_alias)
{
    char *alias;
    size_t index;
    size_t wire_index = (size_t)-1;
    size_t alias_index = (size_t)-1;

    *out_index = (size_t)-1;
    *out_alias = NULL;
    for (index = 0; index < param_count; index++) {
        if (params[index].name != NULL && strcmp(params[index].name, wire_name) == 0) {
            wire_index = index;
            break;
        }
    }
    alias = snake_case(wire_name);
    if (alias == NULL) {
        return TEMPERA_ERR_OUT_OF_MEMORY;
    }
    if (strcmp(alias, wire_name) == 0) {
        tempera_string_free(alias);
        *out_index = wire_index;
        return TEMPERA_OK;
    }
    for (index = 0; index < param_count; index++) {
        if (params[index].name != NULL && strcmp(params[index].name, alias) == 0) {
            alias_index = index;
            break;
        }
    }
    if (wire_index != (size_t)-1 && alias_index != (size_t)-1) {
        *out_alias = alias;
        return TEMPERA_ERR_DUPLICATE_PARAMETER_ALIAS;
    }
    tempera_string_free(alias);
    *out_index = wire_index != (size_t)-1 ? wire_index : alias_index;
    return TEMPERA_OK;
}

/*
 * Validate one path parameter against its declared AIP resource pattern and
 * percent-encode only the `*` segments, so the pattern's structural slashes
 * survive. Rejects empty, "." and ".." segments. NULL on mismatch.
 */
static char *expand_aip_path_param(const char *value, const char *pattern)
{
    tempera_buf buf;
    const char *value_cursor = value;
    const char *pattern_cursor = pattern;

    tempera_buf_init(&buf);
    for (;;) {
        const char *pattern_end = strchr(pattern_cursor, '/');
        const char *value_end = strchr(value_cursor, '/');
        size_t pattern_length =
            pattern_end != NULL ? (size_t)(pattern_end - pattern_cursor) : strlen(pattern_cursor);
        size_t value_length =
            value_end != NULL ? (size_t)(value_end - value_cursor) : strlen(value_cursor);

        if (pattern_length == 1 && pattern_cursor[0] == '*') {
            char *segment;
            char *encoded;

            if (value_length == 0 || (value_length == 1 && value_cursor[0] == '.') ||
                (value_length == 2 && value_cursor[0] == '.' && value_cursor[1] == '.')) {
                tempera_buf_dispose(&buf);
                return NULL;
            }
            segment = tempera_strndup(value_cursor, value_length);
            encoded = segment != NULL ? tempera_url_encode(segment) : NULL;
            tempera_string_free(segment);
            if (encoded == NULL) {
                tempera_buf_dispose(&buf);
                return NULL;
            }
            tempera_buf_append(&buf, encoded);
            tempera_string_free(encoded);
        } else {
            if (pattern_length != value_length ||
                memcmp(pattern_cursor, value_cursor, pattern_length) != 0) {
                tempera_buf_dispose(&buf);
                return NULL;
            }
            tempera_buf_append_bytes(&buf, pattern_cursor, pattern_length);
        }
        if (pattern_end == NULL || value_end == NULL) {
            if (pattern_end != value_end) {
                /* Different segment counts. */
                tempera_buf_dispose(&buf);
                return NULL;
            }
            return tempera_buf_finish(&buf);
        }
        tempera_buf_append_char(&buf, '/');
        pattern_cursor = pattern_end + 1;
        value_cursor = value_end + 1;
    }
}

/* Replace every "{name}" in `path` with `replacement`. */
static char *substitute_path(const char *path, const char *name, const char *replacement)
{
    tempera_buf buf;
    tempera_buf placeholder;
    char *needle;
    const char *cursor = path;

    tempera_buf_init(&placeholder);
    tempera_buf_append_char(&placeholder, '{');
    tempera_buf_append(&placeholder, name);
    tempera_buf_append_char(&placeholder, '}');
    needle = tempera_buf_finish(&placeholder);
    if (needle == NULL) {
        return NULL;
    }
    tempera_buf_init(&buf);
    for (;;) {
        const char *hit = strstr(cursor, needle);

        if (hit == NULL) {
            tempera_buf_append(&buf, cursor);
            break;
        }
        tempera_buf_append_bytes(&buf, cursor, (size_t)(hit - cursor));
        tempera_buf_append(&buf, replacement);
        cursor = hit + strlen(needle);
    }
    tempera_string_free(needle);
    return tempera_buf_finish(&buf);
}

static bool is_idempotency_field(const char *name)
{
    return string_list_contains(IDEMPOTENCY_KEY_FIELDS,
                                sizeof(IDEMPOTENCY_KEY_FIELDS) /
                                    sizeof(IDEMPOTENCY_KEY_FIELDS[0]),
                                name);
}

/*
 * Reject a malformed idempotency key before the request exists, so a retry can
 * never be forced to choose between an unusable key and a freshly minted one.
 * The rule is the canonical tempera-mcp one: exact ASCII-graphic bytes.
 */
static bool valid_idempotency_key(const tempera_param *param)
{
    size_t index;
    size_t length;

    if (param->kind != TEMPERA_PARAM_STRING || param->string_value == NULL) {
        return false;
    }
    length = strlen(param->string_value);
    if (length == 0 || length > TEMPERA_MAX_IDEMPOTENCY_KEY_BYTES) {
        return false;
    }
    for (index = 0; index < length; index++) {
        unsigned char byte = (unsigned char)param->string_value[index];

        if (byte <= 0x20 || byte >= 0x7f) {
            return false;
        }
    }
    return true;
}

/* ------------------------------------------------------------------------ */
/* Requests                                                                  */
/* ------------------------------------------------------------------------ */

void tempera_request_free(tempera_request *request)
{
    size_t index;

    if (request == NULL) {
        return;
    }
    free(request->url);
    for (index = 0; index < request->query_count; index++) {
        free(request->query[index].name);
        free(request->query[index].value);
    }
    free(request->query);
    for (index = 0; index < request->header_count; index++) {
        free(request->headers[index].name);
        free(request->headers[index].value);
    }
    free(request->headers);
    free(request->body_json);
    free(request->body_bytes);
    free(request);
}

char *tempera_request_full_url(const tempera_request *request)
{
    tempera_buf buf;
    size_t index;

    if (request == NULL) {
        return NULL;
    }
    if (request->query_count == 0) {
        return tempera_strdup(request->url);
    }
    tempera_buf_init(&buf);
    tempera_buf_append(&buf, request->url);
    tempera_buf_append_char(&buf, '?');
    for (index = 0; index < request->query_count; index++) {
        char *name = tempera_url_encode(request->query[index].name);
        char *value = tempera_url_encode(request->query[index].value);

        if (name == NULL || value == NULL) {
            tempera_string_free(name);
            tempera_string_free(value);
            tempera_buf_dispose(&buf);
            return NULL;
        }
        if (index > 0) {
            tempera_buf_append_char(&buf, '&');
        }
        tempera_buf_append(&buf, name);
        tempera_buf_append_char(&buf, '=');
        tempera_buf_append(&buf, value);
        tempera_string_free(name);
        tempera_string_free(value);
    }
    return tempera_buf_finish(&buf);
}

const char *tempera_request_header(const tempera_request *request, const char *name)
{
    size_t index;

    if (request == NULL || name == NULL) {
        return NULL;
    }
    for (index = 0; index < request->header_count; index++) {
        if (strcmp(request->headers[index].name, name) == 0) {
            return request->headers[index].value;
        }
    }
    return NULL;
}

const char *tempera_request_query(const tempera_request *request, const char *name)
{
    size_t index;

    if (request == NULL || name == NULL) {
        return NULL;
    }
    for (index = 0; index < request->query_count; index++) {
        if (strcmp(request->query[index].name, name) == 0) {
            return request->query[index].value;
        }
    }
    return NULL;
}

/* ------------------------------------------------------------------------ */
/* Client                                                                    */
/* ------------------------------------------------------------------------ */

tempera_client *tempera_client_new(void)
{
    return (tempera_client *)calloc(1, sizeof(tempera_client));
}

void tempera_client_free(tempera_client *client)
{
    size_t index;

    if (client == NULL) {
        return;
    }
    for (index = 0; index < client->base_url_count; index++) {
        free(client->base_urls[index].product);
        free(client->base_urls[index].url);
    }
    free(client->base_urls);
    free(client->account_token);
    free(client->introspection_secret);
    /* client->auth is borrowed and deliberately not freed here. */
    free(client);
}

tempera_status tempera_client_set_auth(tempera_client *client, const tempera_auth *auth)
{
    if (client == NULL) {
        return TEMPERA_ERR_INVALID_ARGUMENT;
    }
    client->auth = auth;
    return TEMPERA_OK;
}

static tempera_status set_owned_string(char **slot, const char *value)
{
    char *copy = NULL;

    if (value != NULL) {
        copy = tempera_strdup(value);
        if (copy == NULL) {
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
    }
    free(*slot);
    *slot = copy;
    return TEMPERA_OK;
}

tempera_status tempera_client_set_account_token(tempera_client *client, const char *token)
{
    if (client == NULL) {
        return TEMPERA_ERR_INVALID_ARGUMENT;
    }
    return set_owned_string(&client->account_token, token);
}

tempera_status tempera_client_set_introspection_secret(tempera_client *client,
                                                       const char *secret)
{
    if (client == NULL) {
        return TEMPERA_ERR_INVALID_ARGUMENT;
    }
    return set_owned_string(&client->introspection_secret, secret);
}

tempera_status tempera_client_set_base_url(tempera_client *client,
                                           const char *product,
                                           const char *url)
{
    size_t index;
    base_url_entry *grown;
    char *product_copy;
    char *url_copy;

    if (client == NULL || product == NULL || url == NULL) {
        return TEMPERA_ERR_INVALID_ARGUMENT;
    }
    for (index = 0; index < client->base_url_count; index++) {
        if (strcmp(client->base_urls[index].product, product) == 0) {
            return set_owned_string(&client->base_urls[index].url, url);
        }
    }
    product_copy = tempera_strdup(product);
    url_copy = tempera_strdup(url);
    grown = (base_url_entry *)realloc(client->base_urls,
                                      (client->base_url_count + 1) * sizeof(*grown));
    if (product_copy == NULL || url_copy == NULL || grown == NULL) {
        free(product_copy);
        free(url_copy);
        if (grown != NULL) {
            client->base_urls = grown;
        }
        return TEMPERA_ERR_OUT_OF_MEMORY;
    }
    client->base_urls = grown;
    client->base_urls[client->base_url_count].product = product_copy;
    client->base_urls[client->base_url_count].url = url_copy;
    client->base_url_count++;
    return TEMPERA_OK;
}

static const char *client_base_url(const tempera_client *client, const char *product)
{
    size_t index;

    for (index = 0; index < client->base_url_count; index++) {
        if (strcmp(client->base_urls[index].product, product) == 0) {
            return client->base_urls[index].url;
        }
    }
    return NULL;
}

/* State carried through one build, so a single cleanup path can release it. */
typedef struct build_state {
    char *path;
    bool *consumed;
    kv_list query;
    kv_list body;
    bool has_body;
    char *base_url;
    char *body_json;
} build_state;

static void build_state_dispose(build_state *state)
{
    tempera_string_free(state->path);
    free(state->consumed);
    kv_list_dispose(&state->query);
    kv_list_dispose(&state->body);
    tempera_string_free(state->base_url);
    tempera_string_free(state->body_json);
    memset(state, 0, sizeof(*state));
}

tempera_status tempera_client_build_request(const tempera_client *client,
                                            const char *product,
                                            const char *operation,
                                            const tempera_param *params,
                                            size_t param_count,
                                            tempera_request **out_request,
                                            tempera_error *out_error)
{
    const tempera_operation_spec *op;
    const tempera_product_spec *product_spec;

    if (out_request != NULL) {
        *out_request = NULL;
    }
    if (product == NULL || operation == NULL) {
        tempera_error_set(out_error, TEMPERA_ERR_INVALID_ARGUMENT,
                          "build_request requires a product key and an operation id");
        return TEMPERA_ERR_INVALID_ARGUMENT;
    }
    op = tempera_find_operation(product, operation);
    product_spec = tempera_find_product(product);
    if (op == NULL || product_spec == NULL) {
        tempera_error_set(out_error, TEMPERA_ERR_UNKNOWN_OPERATION,
                          "unknown Tempera operation: %s.%s", product, operation);
        return TEMPERA_ERR_UNKNOWN_OPERATION;
    }
    return tempera_client_build_request_spec(client, op, product_spec, params, param_count,
                                             out_request, out_error);
}

tempera_status tempera_client_build_request_spec(const tempera_client *client,
                                                 const tempera_operation_spec *op,
                                                 const tempera_product_spec *product_spec,
                                                 const tempera_param *params,
                                                 size_t param_count,
                                                 tempera_request **out_request,
                                                 tempera_error *out_error)
{
    const char *product;
    const char *operation;
    build_state state;
    tempera_status status;
    tempera_request *request;
    const char *bearer = NULL;
    size_t index;
    size_t length;

    if (out_request != NULL) {
        *out_request = NULL;
    }
    if (client == NULL || op == NULL || product_spec == NULL || out_request == NULL ||
        (params == NULL && param_count > 0)) {
        tempera_error_set(out_error, TEMPERA_ERR_INVALID_ARGUMENT,
                          "build_request requires a client, an operation spec, a product spec, "
                          "and an output pointer");
        return TEMPERA_ERR_INVALID_ARGUMENT;
    }
    product = product_spec->key;
    operation = op->id;

    memset(&state, 0, sizeof(state));
    kv_list_init(&state.query);
    kv_list_init(&state.body);
    if (param_count > 0) {
        state.consumed = (bool *)calloc(param_count, sizeof(*state.consumed));
        if (state.consumed == NULL) {
            tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
    }

    /* Fields the producer derives from the authenticated principal. */
    for (index = 0; index < op->forbidden_body_count; index++) {
        size_t found;
        char *alias = NULL;

        status = declared_param(params, param_count, op->forbidden_body[index], &found, &alias);
        if (status == TEMPERA_ERR_DUPLICATE_PARAMETER_ALIAS) {
            tempera_error_set(out_error, status,
                              "%s.%s: pass either \"%s\" or its snake_case alias \"%s\", not both",
                              product, operation, op->forbidden_body[index], alias);
            tempera_string_free(alias);
            build_state_dispose(&state);
            return status;
        }
        if (status != TEMPERA_OK) {
            tempera_error_set(out_error, status, "out of memory");
            build_state_dispose(&state);
            return status;
        }
        if (found != (size_t)-1) {
            tempera_error_set(out_error, TEMPERA_ERR_FORBIDDEN_BODY_FIELD,
                              "%s.%s: %s is derived from the authenticated principal", product,
                              operation, op->forbidden_body[index]);
            build_state_dispose(&state);
            return TEMPERA_ERR_FORBIDDEN_BODY_FIELD;
        }
    }

    /*
     * Path substitution. Ordinary values are percent-encoded. A producer may
     * declare an AIP resource pattern such as "projects/" plus a wildcard; its structural
     * slash is preserved only after exact template validation.
     */
    state.path = tempera_strdup(op->path);
    if (state.path == NULL) {
        tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
        build_state_dispose(&state);
        return TEMPERA_ERR_OUT_OF_MEMORY;
    }
    for (index = 0; index < op->path_param_count; index++) {
        const char *name = op->path_params[index];
        const char *pattern = NULL;
        size_t found;
        char *alias = NULL;
        char *value;
        char *replacement;
        char *substituted;
        size_t template_index;

        status = declared_param(params, param_count, name, &found, &alias);
        if (status == TEMPERA_ERR_DUPLICATE_PARAMETER_ALIAS) {
            tempera_error_set(out_error, status,
                              "%s.%s: pass either \"%s\" or its snake_case alias \"%s\", not both",
                              product, operation, name, alias);
            tempera_string_free(alias);
            build_state_dispose(&state);
            return status;
        }
        if (status != TEMPERA_OK) {
            tempera_error_set(out_error, status, "out of memory");
            build_state_dispose(&state);
            return status;
        }
        value = found != (size_t)-1 ? param_plain_string(&params[found]) : NULL;
        if (value == NULL || value[0] == '\0') {
            tempera_string_free(value);
            tempera_error_set(out_error, TEMPERA_ERR_MISSING_PATH_PARAM,
                              "%s.%s: missing required path parameter \"%s\"", product, operation,
                              name);
            build_state_dispose(&state);
            return TEMPERA_ERR_MISSING_PATH_PARAM;
        }
        state.consumed[found] = true;
        for (template_index = 0; template_index < op->path_param_template_count;
             template_index++) {
            if (strcmp(op->path_param_templates[template_index].key, name) == 0) {
                pattern = op->path_param_templates[template_index].value;
                break;
            }
        }
        if (pattern != NULL) {
            replacement = expand_aip_path_param(value, pattern);
            if (replacement == NULL) {
                tempera_string_free(value);
                tempera_error_set(out_error, TEMPERA_ERR_INVALID_PATH_PARAM,
                                  "%s.%s: path parameter \"%s\" must match AIP resource pattern "
                                  "\"%s\"",
                                  product, operation, name, pattern);
                build_state_dispose(&state);
                return TEMPERA_ERR_INVALID_PATH_PARAM;
            }
        } else {
            replacement = tempera_url_encode(value);
        }
        tempera_string_free(value);
        if (replacement == NULL) {
            tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
            build_state_dispose(&state);
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
        substituted = substitute_path(state.path, name, replacement);
        tempera_string_free(replacement);
        if (substituted == NULL) {
            tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
            build_state_dispose(&state);
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
        tempera_string_free(state.path);
        state.path = substituted;
    }

    /* Declared query keys. */
    for (index = 0; index < op->query_count; index++) {
        const char *key = op->query[index];
        bool required = string_list_contains(op->required_query, op->required_query_count, key);
        size_t found;
        char *alias = NULL;
        char *value;

        status = declared_param(params, param_count, key, &found, &alias);
        if (status == TEMPERA_ERR_DUPLICATE_PARAMETER_ALIAS) {
            tempera_error_set(out_error, status,
                              "%s.%s: pass either \"%s\" or its snake_case alias \"%s\", not both",
                              product, operation, key, alias);
            tempera_string_free(alias);
            build_state_dispose(&state);
            return status;
        }
        if (status != TEMPERA_OK) {
            tempera_error_set(out_error, status, "out of memory");
            build_state_dispose(&state);
            return status;
        }
        if (found == (size_t)-1) {
            if (required) {
                tempera_error_set(out_error, TEMPERA_ERR_MISSING_QUERY_PARAM,
                                  "%s.%s: missing required query parameter \"%s\"", product,
                                  operation, key);
                build_state_dispose(&state);
                return TEMPERA_ERR_MISSING_QUERY_PARAM;
            }
            continue;
        }
        value = param_plain_string(&params[found]);
        if (value == NULL) {
            tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
            build_state_dispose(&state);
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
        state.consumed[found] = true;
        if (value[0] == '\0' && required) {
            tempera_string_free(value);
            tempera_error_set(out_error, TEMPERA_ERR_MISSING_QUERY_PARAM,
                              "%s.%s: missing required query parameter \"%s\"", product, operation,
                              key);
            build_state_dispose(&state);
            return TEMPERA_ERR_MISSING_QUERY_PARAM;
        }
        kv_list_push_owned(&state.query, tempera_strdup(key), value);
    }

    /* Declared body keys plus body defaults (defaults are JSON strings). */
    if (op->body_count > 0 || op->body_default_count > 0) {
        state.has_body = true;
        for (index = 0; index < op->body_default_count; index++) {
            char *escaped = tempera_json_escape(op->body_defaults[index].value);
            tempera_buf buf;

            if (escaped == NULL) {
                tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
                build_state_dispose(&state);
                return TEMPERA_ERR_OUT_OF_MEMORY;
            }
            tempera_buf_init(&buf);
            tempera_buf_append_char(&buf, '"');
            tempera_buf_append(&buf, escaped);
            tempera_buf_append_char(&buf, '"');
            tempera_string_free(escaped);
            kv_list_push_owned(&state.body, tempera_strdup(op->body_defaults[index].key),
                               tempera_buf_finish(&buf));
        }
        for (index = 0; index < op->body_count; index++) {
            const char *key = op->body[index];
            size_t found;
            char *alias = NULL;

            status = declared_param(params, param_count, key, &found, &alias);
            if (status == TEMPERA_ERR_DUPLICATE_PARAMETER_ALIAS) {
                tempera_error_set(
                    out_error, status,
                    "%s.%s: pass either \"%s\" or its snake_case alias \"%s\", not both", product,
                    operation, key, alias);
                tempera_string_free(alias);
                build_state_dispose(&state);
                return status;
            }
            if (status != TEMPERA_OK) {
                tempera_error_set(out_error, status, "out of memory");
                build_state_dispose(&state);
                return status;
            }
            if (found == (size_t)-1) {
                continue;
            }
            if (is_idempotency_field(key) && !valid_idempotency_key(&params[found])) {
                tempera_error_set(out_error, TEMPERA_ERR_INVALID_IDEMPOTENCY_KEY,
                                  "%s.%s: %s must be 1-%d ASCII-graphic bytes", product, operation,
                                  key, TEMPERA_MAX_IDEMPOTENCY_KEY_BYTES);
                build_state_dispose(&state);
                return TEMPERA_ERR_INVALID_IDEMPOTENCY_KEY;
            }
            kv_list_set_owned(&state.body, key, param_json_fragment(&params[found]));
            state.consumed[found] = true;
        }
    }

    /*
     * Forward compatibility: undeclared parameters flow to the query string on
     * GET/DELETE and into the JSON body otherwise.
     */
    for (index = 0; index < param_count; index++) {
        if (state.consumed[index] || params[index].name == NULL) {
            continue;
        }
        if (strcmp(op->method, "GET") == 0 || strcmp(op->method, "DELETE") == 0) {
            kv_list_push_owned(&state.query, tempera_strdup(params[index].name),
                               param_plain_string(&params[index]));
        } else {
            if (is_idempotency_field(params[index].name) &&
                !valid_idempotency_key(&params[index])) {
                tempera_error_set(out_error, TEMPERA_ERR_INVALID_IDEMPOTENCY_KEY,
                                  "%s.%s: %s must be 1-%d ASCII-graphic bytes", product, operation,
                                  params[index].name, TEMPERA_MAX_IDEMPOTENCY_KEY_BYTES);
                build_state_dispose(&state);
                return TEMPERA_ERR_INVALID_IDEMPOTENCY_KEY;
            }
            state.has_body = true;
            kv_list_set_owned(&state.body, params[index].name,
                              param_json_fragment(&params[index]));
        }
    }

    if (state.query.failed || state.body.failed) {
        tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
        build_state_dispose(&state);
        return TEMPERA_ERR_OUT_OF_MEMORY;
    }

    /* Bearer per the operation's auth kind. */
    if (strcmp(op->auth, "none") == 0) {
        bearer = NULL;
    } else if (strcmp(op->auth, "account") == 0) {
        bearer = client->account_token;
        if (bearer == NULL) {
            tempera_error_set(out_error, TEMPERA_ERR_MISSING_ACCOUNT_TOKEN,
                              "%s: an account token is required; call create_hosted_session first "
                              "or pass tempera_client_set_account_token(...)",
                              product);
            build_state_dispose(&state);
            return TEMPERA_ERR_MISSING_ACCOUNT_TOKEN;
        }
    } else if (strcmp(op->auth, "introspectionSecret") == 0) {
        bearer = client->introspection_secret;
        if (bearer == NULL) {
            tempera_error_set(out_error, TEMPERA_ERR_MISSING_INTROSPECTION_SECRET,
                              "%s: introspect_token requires the introspection secret; pass "
                              "tempera_client_set_introspection_secret(...)",
                              product);
            build_state_dispose(&state);
            return TEMPERA_ERR_MISSING_INTROSPECTION_SECRET;
        }
    } else {
        const char *audience;

        if (strcmp(op->auth, "oauthResource") == 0) {
            audience = op->auth_audience;
            if (audience == NULL) {
                tempera_error_set(out_error, TEMPERA_ERR_INVALID_OPERATION_CONTRACT,
                                  "%s.%s: generated operation auth contract is invalid", product,
                                  operation);
                build_state_dispose(&state);
                return TEMPERA_ERR_INVALID_OPERATION_CONTRACT;
            }
        } else {
            /* "product": the product's audience, or the default audience. */
            audience = product_spec->audience != NULL ? product_spec->audience
                                                      : TEMPERA_DEFAULT_AUDIENCE;
        }
        bearer = tempera_auth_bearer_for(client->auth, audience);
        if (bearer == NULL) {
            tempera_error_set(out_error, TEMPERA_ERR_MISSING_CREDENTIAL,
                              "%s: no credential for audience %s; attach a tempera_auth with "
                              "credentials permitted by this operation",
                              product, audience);
            build_state_dispose(&state);
            return TEMPERA_ERR_MISSING_CREDENTIAL;
        }
    }

    /* Base URL: explicit override, then the product's env var. */
    {
        const char *configured = client_base_url(client, product);

        if (configured == NULL) {
            const char *from_env = getenv(product_spec->env_var);

            if (from_env != NULL && from_env[0] != '\0') {
                configured = from_env;
            }
        }
        if (configured == NULL) {
            tempera_error_set(out_error, TEMPERA_ERR_MISSING_BASE_URL,
                              "missing base URL for %s; set %s or call "
                              "tempera_client_set_base_url(\"%s\", ...)",
                              product, product_spec->env_var, product);
            build_state_dispose(&state);
            return TEMPERA_ERR_MISSING_BASE_URL;
        }
        length = strlen(configured);
        while (length > 0 && configured[length - 1] == '/') {
            length--;
        }
        state.base_url = tempera_strndup(configured, length);
        if (state.base_url == NULL) {
            tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
            build_state_dispose(&state);
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
    }

    /* Serialize the JSON body. */
    if (state.has_body) {
        tempera_buf buf;

        tempera_buf_init(&buf);
        tempera_buf_append_char(&buf, '{');
        for (index = 0; index < state.body.count; index++) {
            char *escaped = tempera_json_escape(state.body.items[index].name);

            if (escaped == NULL) {
                tempera_buf_dispose(&buf);
                tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
                build_state_dispose(&state);
                return TEMPERA_ERR_OUT_OF_MEMORY;
            }
            if (index > 0) {
                tempera_buf_append_char(&buf, ',');
            }
            tempera_buf_append_char(&buf, '"');
            tempera_buf_append(&buf, escaped);
            tempera_buf_append(&buf, "\":");
            tempera_buf_append(&buf, state.body.items[index].value);
            tempera_string_free(escaped);
        }
        tempera_buf_append_char(&buf, '}');
        state.body_json = tempera_buf_finish(&buf);
        if (state.body_json == NULL) {
            tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
            build_state_dispose(&state);
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
    }

    request = (tempera_request *)calloc(1, sizeof(*request));
    if (request == NULL) {
        tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
        build_state_dispose(&state);
        return TEMPERA_ERR_OUT_OF_MEMORY;
    }
    request->method = op->method;
    {
        tempera_buf buf;

        tempera_buf_init(&buf);
        tempera_buf_append(&buf, state.base_url);
        tempera_buf_append(&buf, state.path);
        request->url = tempera_buf_finish(&buf);
    }
    request->query = state.query.items;
    request->query_count = state.query.count;
    kv_list_init(&state.query);
    request->body_json = state.body_json;
    state.body_json = NULL;

    {
        kv_list headers;

        kv_list_init(&headers);
        kv_list_push(&headers, "accept", "application/json");
        if (request->body_json != NULL) {
            kv_list_push(&headers, "content-type", "application/json");
        }
        if (bearer != NULL) {
            tempera_buf buf;

            tempera_buf_init(&buf);
            tempera_buf_append(&buf, "Bearer ");
            tempera_buf_append(&buf, bearer);
            kv_list_push_owned(&headers, tempera_strdup("authorization"),
                               tempera_buf_finish(&buf));
        }
        if (headers.failed || request->url == NULL) {
            kv_list_dispose(&headers);
            tempera_request_free(request);
            tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
            build_state_dispose(&state);
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
        request->headers = headers.items;
        request->header_count = headers.count;
    }

    build_state_dispose(&state);
    if (out_error != NULL) {
        out_error->status = TEMPERA_OK;
        out_error->detail[0] = '\0';
    }
    *out_request = request;
    return TEMPERA_OK;
}

tempera_status tempera_client_build_binary(const tempera_client *client,
                                           const char *product,
                                           const char *operation,
                                           const tempera_param *params,
                                           size_t param_count,
                                           const unsigned char *content,
                                           size_t content_length,
                                           tempera_request **out_request,
                                           tempera_error *out_error)
{
    const tempera_operation_spec *op;
    tempera_request *request = NULL;
    tempera_status status;
    unsigned char *copy = NULL;

    if (out_request != NULL) {
        *out_request = NULL;
    }
    if (client == NULL || product == NULL || operation == NULL || out_request == NULL) {
        tempera_error_set(out_error, TEMPERA_ERR_INVALID_ARGUMENT,
                          "build_binary requires a client, a product, an operation, and an "
                          "output pointer");
        return TEMPERA_ERR_INVALID_ARGUMENT;
    }
    op = tempera_find_operation(product, operation);
    if (op == NULL) {
        tempera_error_set(out_error, TEMPERA_ERR_UNKNOWN_OPERATION,
                          "unknown Tempera operation: %s.%s", product, operation);
        return TEMPERA_ERR_UNKNOWN_OPERATION;
    }
    if (strcmp(op->request_body_kind, "binary") != 0) {
        tempera_error_set(out_error, TEMPERA_ERR_INVALID_OPERATION_CONTRACT,
                          "%s.%s: operation does not declare a binary request body", product,
                          operation);
        return TEMPERA_ERR_INVALID_OPERATION_CONTRACT;
    }
    status = tempera_client_build_request(client, product, operation, params, param_count,
                                          &request, out_error);
    if (status != TEMPERA_OK) {
        return status;
    }
    if (content_length > 0) {
        copy = (unsigned char *)malloc(content_length);
        if (copy == NULL || content == NULL) {
            free(copy);
            tempera_request_free(request);
            tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
        memcpy(copy, content, content_length);
    }
    request->body_bytes = copy;
    request->body_bytes_len = content_length;
    if (op->request_content_type != NULL) {
        kv_list headers;

        headers.items = request->headers;
        headers.count = request->header_count;
        headers.failed = false;
        kv_list_push(&headers, "content-type", op->request_content_type);
        request->headers = headers.items;
        request->header_count = headers.count;
        if (headers.failed) {
            tempera_request_free(request);
            tempera_error_set(out_error, TEMPERA_ERR_OUT_OF_MEMORY, "out of memory");
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
    }
    *out_request = request;
    return TEMPERA_OK;
}
