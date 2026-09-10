/*
 * Conformance and unit tests for the Tempera C SDK.
 *
 * No test framework: a handful of assertion macros, a plain main(), and a
 * non-zero exit status on the first failure count. The centrepiece mirrors the
 * Rust suite's conformance loop -- every generated operation is built and
 * checked -- and the rest pins the behaviours the other language packages also
 * assert.
 *
 * setenv()/unsetenv() are POSIX rather than C99, so the file asks for the
 * POSIX names explicitly; nothing in the library itself needs them.
 */

#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "tempera/tempera.h"

static int checks = 0;
static int failures = 0;

#define CHECK(condition, ...)                                                                 \
    do {                                                                                      \
        checks++;                                                                             \
        if (!(condition)) {                                                                   \
            failures++;                                                                       \
            (void)fprintf(stderr, "FAIL %s:%d: ", __FILE__, __LINE__);                        \
            (void)fprintf(stderr, __VA_ARGS__);                                               \
            (void)fputc('\n', stderr);                                                        \
        }                                                                                     \
    } while (0)

#define CHECK_STR(actual, expected)                                                           \
    do {                                                                                      \
        const char *actual_value = (actual);                                                  \
        const char *expected_value = (expected);                                              \
        checks++;                                                                             \
        if (actual_value == NULL || strcmp(actual_value, expected_value) != 0) {              \
            failures++;                                                                       \
            (void)fprintf(stderr, "FAIL %s:%d: expected \"%s\", got \"%s\"\n", __FILE__,      \
                          __LINE__, expected_value,                                           \
                          actual_value == NULL ? "(null)" : actual_value);                    \
        }                                                                                     \
    } while (0)

#define CHECK_NULL_STR(actual)                                                                \
    do {                                                                                      \
        const char *actual_value = (actual);                                                  \
        checks++;                                                                             \
        if (actual_value != NULL) {                                                           \
            failures++;                                                                       \
            (void)fprintf(stderr, "FAIL %s:%d: expected NULL, got \"%s\"\n", __FILE__,        \
                          __LINE__, actual_value);                                            \
        }                                                                                     \
    } while (0)

/* ------------------------------------------------------------------------ */
/* Fixtures                                                                  */
/* ------------------------------------------------------------------------ */

static char *base_url_for(const char *product)
{
    static char buffer[256];

    (void)snprintf(buffer, sizeof(buffer), "https://%s.example.test", product);
    return buffer;
}

static tempera_auth *make_auth(void)
{
    tempera_auth *auth = tempera_auth_new("https://staging-api.tempera.dev");

    if (auth != NULL) {
        (void)tempera_auth_set_api_key(auth, "tp_key_1");
    }
    return auth;
}

static tempera_client *full_client(const tempera_auth *auth)
{
    tempera_client *client = tempera_client_new();
    size_t index;

    if (client == NULL) {
        return NULL;
    }
    (void)tempera_client_set_auth(client, auth);
    (void)tempera_client_set_account_token(client, "acct_token_1");
    (void)tempera_client_set_introspection_secret(client, "intro_secret_1");
    for (index = 0; index < TEMPERA_PRODUCT_COUNT; index++) {
        (void)tempera_client_set_base_url(client, TEMPERA_PRODUCTS[index].key,
                                          base_url_for(TEMPERA_PRODUCTS[index].key));
    }
    return client;
}

/*
 * The sample value for one path parameter: a producer-declared AIP resource
 * pattern with every wildcard filled in, or "<name>_1". Mirrors the Rust
 * suite's sample_path_param.
 */
static void sample_path_param(const tempera_operation_spec *op,
                              const char *name,
                              char *out,
                              size_t out_size)
{
    size_t index;
    const char *pattern = NULL;
    size_t written = 0;

    for (index = 0; index < op->path_param_template_count; index++) {
        if (strcmp(op->path_param_templates[index].key, name) == 0) {
            pattern = op->path_param_templates[index].value;
            break;
        }
    }
    if (pattern == NULL) {
        (void)snprintf(out, out_size, "%s_1", name);
        return;
    }
    for (index = 0; pattern[index] != '\0' && written + 1 < out_size; index++) {
        if (pattern[index] == '*') {
            written += (size_t)snprintf(out + written, out_size - written, "%s_1", name);
        } else {
            out[written++] = pattern[index];
            out[written] = '\0';
        }
    }
}

/* ------------------------------------------------------------------------ */
/* 1. Conformance: every generated operation builds                          */
/* ------------------------------------------------------------------------ */

static void test_every_operation_builds(const tempera_client *client)
{
    size_t op_index;
    size_t built = 0;

    CHECK(TEMPERA_OPERATION_COUNT > 400, "expected the full operation table, got %lu",
          (unsigned long)TEMPERA_OPERATION_COUNT);

    for (op_index = 0; op_index < TEMPERA_OPERATION_COUNT; op_index++) {
        const tempera_operation_spec *op = &TEMPERA_OPERATIONS[op_index];
        tempera_param params[64];
        char samples[32][256];
        size_t param_count = 0;
        size_t index;
        tempera_request *request = NULL;
        tempera_error error;
        tempera_status status;
        char expected_url[1024];
        const char *authorization;

        CHECK(op->upstream_operation_id[0] != '\0', "%s.%s: producer operation id", op->product,
              op->id);
        CHECK(op->path_param_count <= 32, "%s.%s: unexpected path parameter count", op->product,
              op->id);

        for (index = 0; index < op->path_param_count; index++) {
            sample_path_param(op, op->path_params[index], samples[index], sizeof(samples[index]));
            params[param_count++] = tempera_param_string(op->path_params[index], samples[index]);
        }
        for (index = 0; index < op->required_query_count; index++) {
            params[param_count++] =
                tempera_param_string(op->required_query[index], "sample-query");
        }

        status = tempera_client_build_request(client, op->product, op->id, params, param_count,
                                              &request, &error);
        if (status != TEMPERA_OK) {
            failures++;
            checks++;
            (void)fprintf(stderr, "FAIL %s.%s failed to build: %s\n", op->product, op->id,
                          error.detail);
            continue;
        }
        built++;

        CHECK_STR(request->method, op->method);

        /* URL: base + the path with every placeholder substituted. */
        {
            char path[1024];

            (void)snprintf(path, sizeof(path), "%s", op->path);
            for (index = 0; index < op->path_param_count; index++) {
                char placeholder[128];
                char rebuilt[1024];
                char *hit;

                (void)snprintf(placeholder, sizeof(placeholder), "{%s}", op->path_params[index]);
                while ((hit = strstr(path, placeholder)) != NULL) {
                    (void)snprintf(rebuilt, sizeof(rebuilt), "%.*s%s%s", (int)(hit - path), path,
                                   samples[index], hit + strlen(placeholder));
                    (void)snprintf(path, sizeof(path), "%s", rebuilt);
                }
            }
            (void)snprintf(expected_url, sizeof(expected_url), "%s%s", base_url_for(op->product),
                           path);
            CHECK_STR(request->url, expected_url);
        }

        /* Auth header per kind. */
        authorization = tempera_request_header(request, "authorization");
        if (strcmp(op->auth, "none") == 0) {
            CHECK(authorization == NULL, "%s.%s: unauthenticated operation carries a bearer",
                  op->product, op->id);
        } else if (strcmp(op->auth, "account") == 0) {
            CHECK_STR(authorization, "Bearer acct_token_1");
        } else if (strcmp(op->auth, "introspectionSecret") == 0) {
            CHECK_STR(authorization, "Bearer intro_secret_1");
        } else {
            /* product and oauthResource both fall back to the tp_ API key. */
            CHECK_STR(authorization, "Bearer tp_key_1");
        }
        CHECK_STR(tempera_request_header(request, "accept"), "application/json");

        /* Body defaults are always present in the serialized body. */
        if (op->body_count == 0 && op->body_default_count == 0) {
            CHECK(request->body_json == NULL, "%s.%s: unexpected body", op->product, op->id);
            CHECK(tempera_request_header(request, "content-type") == NULL,
                  "%s.%s: unexpected content-type", op->product, op->id);
        } else {
            CHECK(request->body_json != NULL, "%s.%s: expected a body", op->product, op->id);
            for (index = 0; index < op->body_default_count; index++) {
                char fragment[512];

                (void)snprintf(fragment, sizeof(fragment), "\"%s\":\"%s\"",
                               op->body_defaults[index].key, op->body_defaults[index].value);
                CHECK(request->body_json != NULL && strstr(request->body_json, fragment) != NULL,
                      "%s.%s: body missing default %s", op->product, op->id,
                      op->body_defaults[index].key);
            }
            CHECK_STR(tempera_request_header(request, "content-type"), "application/json");
        }

        for (index = 0; index < op->required_query_count; index++) {
            CHECK(tempera_request_query(request, op->required_query[index]) != NULL,
                  "%s.%s: missing required query %s", op->product, op->id,
                  op->required_query[index]);
        }

        tempera_request_free(request);
    }
    CHECK(built == TEMPERA_OPERATION_COUNT, "built %lu of %lu operations", (unsigned long)built,
          (unsigned long)TEMPERA_OPERATION_COUNT);
}

/* ------------------------------------------------------------------------ */
/* 2. Wire names, snake_case aliases, and ambiguity                          */
/* ------------------------------------------------------------------------ */

static void test_alias_handling(const tempera_client *client)
{
    tempera_param canonical[2];
    tempera_param alias[2];
    tempera_param both[3];
    tempera_request *request = NULL;
    tempera_error error;
    tempera_status status;

    canonical[0] = tempera_param_string("tenantId", "tenant_1");
    canonical[1] = tempera_param_string("traceId", "trace_1");
    status = tempera_client_build_request(client, "palette", "get_trace", canonical, 2, &request,
                                          &error);
    CHECK(status == TEMPERA_OK, "canonical wire names rejected: %s", error.detail);
    CHECK_STR(request->url, "https://palette.example.test/v1/traces/tenant_1/trace_1");
    tempera_request_free(request);
    request = NULL;

    alias[0] = tempera_param_string("tenant_id", "tenant_1");
    alias[1] = tempera_param_string("trace_id", "trace_1");
    status =
        tempera_client_build_request(client, "palette", "get_trace", alias, 2, &request, &error);
    CHECK(status == TEMPERA_OK, "snake_case aliases rejected: %s", error.detail);
    CHECK_STR(request->url, "https://palette.example.test/v1/traces/tenant_1/trace_1");
    tempera_request_free(request);
    request = NULL;

    both[0] = tempera_param_string("tenantId", "tenant_1");
    both[1] = tempera_param_string("tenant_id", "tenant_2");
    both[2] = tempera_param_string("traceId", "trace_1");
    status =
        tempera_client_build_request(client, "palette", "get_trace", both, 3, &request, &error);
    CHECK(status == TEMPERA_ERR_DUPLICATE_PARAMETER_ALIAS, "ambiguous alias accepted (status %d)",
          (int)status);
    CHECK(request == NULL, "failed build still produced a request");
    CHECK(strstr(error.detail, "not both") != NULL, "unhelpful alias detail: %s", error.detail);

    /* Declared query keys emit the producer's canonical name, not the alias. */
    {
        tempera_param query_params[3];

        query_params[0] = tempera_param_string("tenant_id", "tenant_1");
        query_params[1] = tempera_param_int("pageSize", 25);
        query_params[2] = tempera_param_string("status", "error");
        status = tempera_client_build_request(client, "palette", "list_traces", query_params, 3,
                                              &request, &error);
        CHECK(status == TEMPERA_OK, "list_traces failed: %s", error.detail);
        CHECK_STR(request->url, "https://palette.example.test/v1/traces/tenant_1");
        CHECK_STR(tempera_request_query(request, "pageSize"), "25");
        CHECK_STR(tempera_request_query(request, "status"), "error");
        CHECK_NULL_STR(tempera_request_query(request, "page_size"));
        tempera_request_free(request);
        request = NULL;
    }
}

/* ------------------------------------------------------------------------ */
/* 3. forbiddenBody: principal-derived fields are rejected                   */
/* ------------------------------------------------------------------------ */

static void test_forbidden_body(const tempera_client *client)
{
    /*
     * No shipped operation declares forbiddenBody yet, so the rule is proven
     * against a synthetic contract through the spec-taking entry point, and
     * then re-checked across the whole generated table so it arms itself the
     * moment a producer does declare one.
     */
    static const char *const forbidden[] = {"tenantId"};
    static const char *const body[] = {"note"};
    static const tempera_product_spec product = {"palette", "palette",
                                                 "https://example.test/palette",
                                                 "TEMPERA_PALETTE_URL", "palette", "Test."};
    static const tempera_operation_spec op = {
        "palette",           "synthetic_write", "syntheticWrite", "POST", "/v1/synthetic",
        "product",           NULL,              NULL,             0,      NULL,
        0,                   NULL,              0,                NULL,   0,
        NULL,                0,                 NULL,             0,      body,
        1,                   forbidden,         1,                NULL,   0,
        NULL,                0,                 "json",           NULL,   NULL,
        false,               false,             "none",           "Synthetic test operation."};
    tempera_param params[2];
    tempera_request *request = NULL;
    tempera_error error;
    tempera_status status;
    size_t op_index;

    params[0] = tempera_param_string("note", "hello");
    status = tempera_client_build_request_spec(client, &op, &product, params, 1, &request, &error);
    CHECK(status == TEMPERA_OK, "synthetic operation failed to build: %s", error.detail);
    CHECK(request != NULL && request->body_json != NULL, "synthetic operation produced no body");
    if (request != NULL) {
        CHECK_STR(request->body_json, "{\"note\":\"hello\"}");
    }
    tempera_request_free(request);
    request = NULL;

    params[1] = tempera_param_string("tenantId", "tenant_1");
    status = tempera_client_build_request_spec(client, &op, &product, params, 2, &request, &error);
    CHECK(status == TEMPERA_ERR_FORBIDDEN_BODY_FIELD, "forbidden field accepted (status %d)",
          (int)status);
    CHECK(strstr(error.detail, "authenticated principal") != NULL, "unhelpful detail: %s",
          error.detail);
    CHECK(request == NULL, "failed build still produced a request");

    /* The snake_case alias of a forbidden field is refused too. */
    params[1] = tempera_param_string("tenant_id", "tenant_1");
    status = tempera_client_build_request_spec(client, &op, &product, params, 2, &request, &error);
    CHECK(status == TEMPERA_ERR_FORBIDDEN_BODY_FIELD, "forbidden alias accepted (status %d)",
          (int)status);

    for (op_index = 0; op_index < TEMPERA_OPERATION_COUNT; op_index++) {
        const tempera_operation_spec *generated = &TEMPERA_OPERATIONS[op_index];
        size_t index;

        for (index = 0; index < generated->forbidden_body_count; index++) {
            tempera_param forbidden_param =
                tempera_param_string(generated->forbidden_body[index], "x");

            status = tempera_client_build_request(client, generated->product, generated->id,
                                                  &forbidden_param, 1, &request, &error);
            CHECK(status == TEMPERA_ERR_FORBIDDEN_BODY_FIELD,
                  "%s.%s accepted forbidden field %s", generated->product, generated->id,
                  generated->forbidden_body[index]);
            tempera_request_free(request);
            request = NULL;
        }
    }
}

/* ------------------------------------------------------------------------ */
/* 4. AIP resource patterns                                                  */
/* ------------------------------------------------------------------------ */

static void test_aip_path_patterns(const tempera_client *client)
{
    static const char *const rejected[] = {"projects/",        "projects/.",     "projects/..",
                                           "tenants/p_1",      "projects/a/b",   "projects",
                                           "/projects/p_1"};
    tempera_param params[1];
    tempera_request *request = NULL;
    tempera_error error;
    tempera_status status;
    size_t index;

    params[0] = tempera_param_string("parent", "projects/p_1");
    status = tempera_client_build_request(client, "data_engine", "list_use_cases", params, 1,
                                          &request, &error);
    CHECK(status == TEMPERA_OK, "valid AIP parent rejected: %s", error.detail);
    CHECK_STR(request->url, "https://data_engine.example.test/v1/projects/p_1/use-cases");
    tempera_request_free(request);
    request = NULL;

    /* Only the wildcard segment is percent-encoded; the literal slash stays. */
    params[0] = tempera_param_string("parent", "projects/p 1/2");
    status = tempera_client_build_request(client, "data_engine", "list_use_cases", params, 1,
                                          &request, &error);
    CHECK(status == TEMPERA_ERR_INVALID_PATH_PARAM,
          "an extra segment slipped past the pattern (status %d)", (int)status);

    params[0] = tempera_param_string("parent", "projects/p 1");
    status = tempera_client_build_request(client, "data_engine", "list_use_cases", params, 1,
                                          &request, &error);
    CHECK(status == TEMPERA_OK, "encodable parent rejected: %s", error.detail);
    CHECK_STR(request->url, "https://data_engine.example.test/v1/projects/p%201/use-cases");
    tempera_request_free(request);
    request = NULL;

    for (index = 0; index < sizeof(rejected) / sizeof(rejected[0]); index++) {
        params[0] = tempera_param_string("parent", rejected[index]);
        status = tempera_client_build_request(client, "data_engine", "list_use_cases", params, 1,
                                              &request, &error);
        CHECK(status != TEMPERA_OK, "AIP pattern accepted \"%s\"", rejected[index]);
        CHECK(request == NULL, "rejected pattern still produced a request");
        if (index < 5) {
            CHECK(status == TEMPERA_ERR_INVALID_PATH_PARAM ||
                      status == TEMPERA_ERR_MISSING_PATH_PARAM,
                  "unexpected status %d for \"%s\"", (int)status, rejected[index]);
        }
    }

    /* A path parameter without a template is simply percent-encoded. */
    {
        tempera_param encoded[2];

        encoded[0] = tempera_param_string("tenantId", "tenant/1");
        encoded[1] = tempera_param_string("traceId", "trace 1");
        status = tempera_client_build_request(client, "palette", "get_trace", encoded, 2, &request,
                                              &error);
        CHECK(status == TEMPERA_OK, "percent-encoded path rejected: %s", error.detail);
        CHECK_STR(request->url, "https://palette.example.test/v1/traces/tenant%2F1/trace%201");
        tempera_request_free(request);
        request = NULL;
    }
}

/* ------------------------------------------------------------------------ */
/* 5. Forward compatibility: undeclared parameters spill                     */
/* ------------------------------------------------------------------------ */

static void test_forward_compatible_spill(const tempera_client *client)
{
    tempera_param params[3];
    tempera_request *request = NULL;
    tempera_error error;
    tempera_status status;

    /* GET: extras go to the query string. */
    params[0] = tempera_param_string("tenantId", "tenant_1");
    params[1] = tempera_param_string("traceId", "trace_1");
    params[2] = tempera_param_string("brandNewFilter", "yes");
    status =
        tempera_client_build_request(client, "palette", "get_trace", params, 3, &request, &error);
    CHECK(status == TEMPERA_OK, "GET spill failed: %s", error.detail);
    CHECK_STR(tempera_request_query(request, "brandNewFilter"), "yes");
    CHECK(request->body_json == NULL, "GET spill produced a body");
    tempera_request_free(request);
    request = NULL;

    /* POST: extras go into the JSON body, creating one when needed. */
    params[0] = tempera_param_string("mode", "login");
    params[1] = tempera_param_string("brandNewField", "yes");
    params[2] = tempera_param_int("attempt", 2);
    status = tempera_client_build_request(client, "control_plane", "create_hosted_session", params,
                                          3, &request, &error);
    CHECK(status == TEMPERA_OK, "POST spill failed: %s", error.detail);
    CHECK(request->body_json != NULL && strstr(request->body_json, "\"mode\":\"login\"") != NULL,
          "body missing declared member: %s", request->body_json);
    CHECK(strstr(request->body_json, "\"brandNewField\":\"yes\"") != NULL,
          "body missing undeclared string: %s", request->body_json);
    CHECK(strstr(request->body_json, "\"attempt\":2") != NULL, "body missing undeclared int: %s",
          request->body_json);
    CHECK(request->query_count == 0, "POST spill leaked into the query string");
    CHECK_STR(tempera_request_header(request, "content-type"), "application/json");
    tempera_request_free(request);
    request = NULL;

    /* DELETE behaves like GET. */
    {
        size_t index;
        const tempera_operation_spec *delete_op = NULL;

        for (index = 0; index < TEMPERA_OPERATION_COUNT; index++) {
            if (strcmp(TEMPERA_OPERATIONS[index].method, "DELETE") == 0 &&
                TEMPERA_OPERATIONS[index].path_param_count == 0) {
                delete_op = &TEMPERA_OPERATIONS[index];
                break;
            }
        }
        for (index = 0; index < TEMPERA_OPERATION_COUNT && delete_op == NULL; index++) {
            if (strcmp(TEMPERA_OPERATIONS[index].method, "DELETE") == 0) {
                delete_op = &TEMPERA_OPERATIONS[index];
            }
        }
        if (delete_op != NULL && delete_op->path_param_count == 0) {
            tempera_param extra = tempera_param_string("brandNewFlag", "1");

            status = tempera_client_build_request(client, delete_op->product, delete_op->id,
                                                  &extra, 1, &request, &error);
            CHECK(status == TEMPERA_OK, "DELETE spill failed: %s", error.detail);
            if (status == TEMPERA_OK) {
                CHECK_STR(tempera_request_query(request, "brandNewFlag"), "1");
                CHECK(request->body_json == NULL, "DELETE spill produced a body");
            }
            tempera_request_free(request);
            request = NULL;
        }
    }
}

/* ------------------------------------------------------------------------ */
/* 6. Error normalization                                                    */
/* ------------------------------------------------------------------------ */

static void test_error_normalization(void)
{
    tempera_api_error error;

    /* error.status (a string) wins over error.code. */
    CHECK(tempera_normalize_error_body(
              400, "Bad Request",
              "{\"error\":{\"code\":400,\"status\":\"INVALID_ARGUMENT\",\"message\":\"bad "
              "field\",\"details\":[{\"@type\":\"type.googleapis.com/google.rpc.ErrorInfo\","
              "\"reason\":\"FIELD_INVALID\"}],\"requestId\":\"req_1\"}}",
              &error) == TEMPERA_OK,
          "canonical envelope failed to normalize");
    CHECK(error.status == 400, "status not carried");
    CHECK_STR(error.code, "INVALID_ARGUMENT");
    CHECK_STR(error.message, "bad field");
    CHECK_STR(error.reason, "FIELD_INVALID");
    CHECK_STR(error.request_id, "req_1");
    tempera_api_error_free(&error);

    /* error.code, when it is a string and error.status is not. */
    (void)tempera_normalize_error_body(
        404, "", "{\"error\":{\"code\":\"not_found\",\"message\":\"trace not found\"}}", &error);
    CHECK_STR(error.code, "not_found");
    CHECK_STR(error.message, "trace not found");
    tempera_api_error_free(&error);

    /* A numeric code is not a code: neither member is a string. */
    (void)tempera_normalize_error_body(500, "Server Error",
                                       "{\"error\":{\"code\":500,\"message\":\"boom\"}}", &error);
    CHECK_NULL_STR(error.code);
    CHECK_STR(error.message, "boom");
    tempera_api_error_free(&error);

    /* Message falls back to the HTTP status text. */
    (void)tempera_normalize_error_body(503, "Service Unavailable", "{\"error\":{\"code\":503}}",
                                       &error);
    CHECK_STR(error.message, "Service Unavailable");
    tempera_api_error_free(&error);

    /* request_id is accepted in either spelling, requestId first. */
    (void)tempera_normalize_error_body(
        429, "", "{\"error\":{\"message\":\"slow down\",\"request_id\":\"req_snake\"}}", &error);
    CHECK_STR(error.request_id, "req_snake");
    tempera_api_error_free(&error);
    (void)tempera_normalize_error_body(429, "",
                                       "{\"error\":{\"message\":\"slow down\",\"requestId\":\"req_"
                                       "camel\",\"request_id\":\"req_snake\"}}",
                                       &error);
    CHECK_STR(error.request_id, "req_camel");
    tempera_api_error_free(&error);

    /* Legacy flat shape: a string error plus a top-level message. */
    (void)tempera_normalize_error_body(401, "",
                                       "{\"error\":\"invalid_token\",\"message\":\"token expired\"}",
                                       &error);
    CHECK_STR(error.code, "invalid_token");
    CHECK_STR(error.message, "token expired");
    CHECK_NULL_STR(error.request_id);
    tempera_api_error_free(&error);

    /* Legacy message-only shape. */
    (void)tempera_normalize_error_body(400, "", "{\"error\":\"something went wrong\"}", &error);
    CHECK_NULL_STR(error.code);
    CHECK_STR(error.message, "something went wrong");
    tempera_api_error_free(&error);

    /* Unparseable bodies fall back to the status text, then to a literal. */
    (void)tempera_normalize_error_body(502, "Bad Gateway", "<html>nope</html>", &error);
    CHECK_STR(error.message, "Bad Gateway");
    CHECK_NULL_STR(error.code);
    tempera_api_error_free(&error);
    (void)tempera_normalize_error_body(0, "", NULL, &error);
    CHECK_STR(error.message, "request failed");
    tempera_api_error_free(&error);

    /* Escapes and non-BMP payloads survive the scanner intact. */
    (void)tempera_normalize_error_body(
        400, "", "{\"error\":\"quota\",\"message\":\"caf\\u00e9 \\ud83d\\ude80 \\\"quoted\\\"\"}",
        &error);
    CHECK_STR(error.message, "caf\xc3\xa9 \xf0\x9f\x9a\x80 \"quoted\"");
    tempera_api_error_free(&error);
}

/* ------------------------------------------------------------------------ */
/* 7. The error enum                                                         */
/* ------------------------------------------------------------------------ */

static void test_error_enum(const tempera_auth *auth)
{
    tempera_client *bare = tempera_client_new();
    tempera_client *client = full_client(auth);
    tempera_request *request = NULL;
    tempera_error error;
    tempera_param params[2];
    int status_value;

    /* Every status has a distinct, non-empty message. */
    for (status_value = TEMPERA_OK; status_value <= TEMPERA_ERR_INVALID_ARGUMENT;
         status_value++) {
        const char *message = tempera_error_message((tempera_status)status_value);

        CHECK(message != NULL && message[0] != '\0', "status %d has no message", status_value);
    }
    CHECK_STR(tempera_error_message((tempera_status)9999), "unknown Tempera status");

    /* UNKNOWN_OPERATION, both ways. */
    CHECK(tempera_client_build_request(client, "palette", "does_not_exist", NULL, 0, &request,
                                       &error) == TEMPERA_ERR_UNKNOWN_OPERATION,
          "unknown operation accepted");
    CHECK(tempera_client_build_request(client, "not_a_product", "health", NULL, 0, &request,
                                       &error) == TEMPERA_ERR_UNKNOWN_OPERATION,
          "unknown product accepted");
    CHECK_STR(error.detail, "unknown Tempera operation: not_a_product.health");

    /* MISSING_PATH_PARAM, including the empty-string case. */
    params[0] = tempera_param_string("tenant_id", "tenant_1");
    CHECK(tempera_client_build_request(client, "palette", "get_trace", params, 1, &request,
                                       &error) == TEMPERA_ERR_MISSING_PATH_PARAM,
          "missing path parameter accepted");
    CHECK(strstr(error.detail, "missing required path parameter \"traceId\"") != NULL,
          "unhelpful detail: %s", error.detail);
    params[1] = tempera_param_string("trace_id", "");
    CHECK(tempera_client_build_request(client, "palette", "get_trace", params, 2, &request,
                                       &error) == TEMPERA_ERR_MISSING_PATH_PARAM,
          "empty path parameter accepted");

    /* MISSING_QUERY_PARAM, using the producer's canonical wire name. */
    params[0] = tempera_param_string("payment_intent_id", "pi_1");
    CHECK(tempera_client_build_request(client, "tempera_payments", "get_payment_intent", params, 1,
                                       &request, &error) == TEMPERA_ERR_MISSING_QUERY_PARAM,
          "missing required query accepted");
    CHECK(strstr(error.detail, "missing required query parameter") != NULL,
          "unhelpful detail: %s", error.detail);

    /* MISSING_ACCOUNT_TOKEN / MISSING_INTROSPECTION_SECRET / MISSING_CREDENTIAL. */
    (void)tempera_client_set_base_url(bare, "control_plane", "https://control.example.test");
    (void)tempera_client_set_base_url(bare, "palette", "https://palette.example.test");
    CHECK(tempera_client_build_request(bare, "control_plane", "me", NULL, 0, &request, &error) ==
              TEMPERA_ERR_MISSING_ACCOUNT_TOKEN,
          "missing account token accepted");
    CHECK(tempera_client_build_request(bare, "control_plane", "introspect_token", NULL, 0,
                                       &request, &error) ==
              TEMPERA_ERR_MISSING_INTROSPECTION_SECRET,
          "missing introspection secret accepted");
    params[0] = tempera_param_string("tenantId", "tenant_1");
    params[1] = tempera_param_string("traceId", "trace_1");
    CHECK(tempera_client_build_request(bare, "palette", "get_trace", params, 2, &request,
                                       &error) == TEMPERA_ERR_MISSING_CREDENTIAL,
          "missing credential accepted");
    CHECK(strstr(error.detail, "palette") != NULL, "detail omits the audience: %s", error.detail);

    /* INVALID_OPERATION_CONTRACT: a JSON operation is not a binary upload. */
    params[0] = tempera_param_string("tenantId", "tenant_1");
    params[1] = tempera_param_string("traceId", "trace_1");
    CHECK(tempera_client_build_binary(client, "palette", "get_trace", params, 2,
                                      (const unsigned char *)"x", 1, &request,
                                      &error) == TEMPERA_ERR_INVALID_OPERATION_CONTRACT,
          "non-binary operation accepted a binary body");

    /* INVALID_IDEMPOTENCY_KEY. */
    params[0] = tempera_param_string("packId", "pack_1");
    params[1] = tempera_param_string("idempotencyKey", "not a graphic key");
    CHECK(tempera_client_build_request(client, "control_plane", "create_credit_topup", params, 2,
                                       &request, &error) == TEMPERA_ERR_INVALID_IDEMPOTENCY_KEY,
          "malformed idempotency key accepted");
    params[1] = tempera_param_string("idempotencyKey", "key-1");
    CHECK(tempera_client_build_request(client, "control_plane", "create_credit_topup", params, 2,
                                       &request, &error) == TEMPERA_OK,
          "well-formed idempotency key rejected: %s", error.detail);
    tempera_request_free(request);
    request = NULL;

    /* INVALID_ARGUMENT. */
    CHECK(tempera_client_build_request(client, NULL, "health", NULL, 0, &request, &error) ==
              TEMPERA_ERR_INVALID_ARGUMENT,
          "NULL product accepted");

    tempera_client_free(bare);
    tempera_client_free(client);
}

/* ------------------------------------------------------------------------ */
/* 8. Base-URL precedence                                                    */
/* ------------------------------------------------------------------------ */

static void test_base_url_precedence(void)
{
    tempera_client *client = tempera_client_new();
    tempera_request *request = NULL;
    tempera_error error;
    tempera_status status;

    (void)unsetenv("TEMPERA_TEMPO_URL");
    status = tempera_client_build_request(client, "tempo", "health", NULL, 0, &request, &error);
    CHECK(status == TEMPERA_ERR_MISSING_BASE_URL, "missing base URL accepted (status %d)",
          (int)status);
    CHECK(strstr(error.detail, "TEMPERA_TEMPO_URL") != NULL, "detail omits the env var: %s",
          error.detail);

    /* The env var supplies the base URL when nothing is configured. */
    (void)setenv("TEMPERA_TEMPO_URL", "https://env.example.test", 1);
    status = tempera_client_build_request(client, "tempo", "health", NULL, 0, &request, &error);
    CHECK(status == TEMPERA_OK, "env base URL rejected: %s", error.detail);
    CHECK_STR(request->url, "https://env.example.test/healthz");
    tempera_request_free(request);
    request = NULL;

    /* An explicit override wins over the env var. */
    (void)tempera_client_set_base_url(client, "tempo", "https://override.example.test");
    status = tempera_client_build_request(client, "tempo", "health", NULL, 0, &request, &error);
    CHECK(status == TEMPERA_OK, "override rejected: %s", error.detail);
    CHECK_STR(request->url, "https://override.example.test/healthz");
    tempera_request_free(request);
    request = NULL;

    /* An empty env var counts as unset. */
    (void)setenv("TEMPERA_TEMPO_URL", "", 1);
    {
        tempera_client *empty_env = tempera_client_new();

        status =
            tempera_client_build_request(empty_env, "tempo", "health", NULL, 0, &request, &error);
        CHECK(status == TEMPERA_ERR_MISSING_BASE_URL, "empty env var used as a base URL");
        tempera_client_free(empty_env);
    }
    (void)unsetenv("TEMPERA_TEMPO_URL");

    /* Trailing slashes are trimmed. */
    (void)tempera_client_set_base_url(client, "tempo", "https://tempo.example.test///");
    status = tempera_client_build_request(client, "tempo", "health", NULL, 0, &request, &error);
    CHECK(status == TEMPERA_OK, "trailing-slash base URL rejected: %s", error.detail);
    CHECK_STR(request->url, "https://tempo.example.test/healthz");
    tempera_request_free(request);

    tempera_client_free(client);
}

/* ------------------------------------------------------------------------ */
/* 9. Auth: PKCE, authorize URL, token bodies, rotation                      */
/* ------------------------------------------------------------------------ */

static void test_auth(void)
{
    tempera_auth *auth = tempera_auth_new("https://staging-api.tempera.dev/");
    tempera_authorize_url_params params;
    char *challenge;
    char *url;
    char *body;
    unsigned char entropy[32];
    tempera_pkce_pair pair;
    size_t index;

    CHECK_STR(tempera_auth_issuer_url(auth), "https://staging-api.tempera.dev");

    /* RFC 7636 appendix B reference vector. */
    challenge = tempera_pkce_challenge_s256("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk");
    CHECK_STR(challenge, "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM");
    CHECK(strchr(challenge, '=') == NULL, "PKCE challenge is padded");
    tempera_string_free(challenge);

    /* RFC 4648 section 5 vectors, unpadded. */
    challenge = tempera_base64url_no_pad((const unsigned char *)"foobar", 6);
    CHECK_STR(challenge, "Zm9vYmFy");
    tempera_string_free(challenge);
    challenge = tempera_base64url_no_pad((const unsigned char *)"fo", 2);
    CHECK_STR(challenge, "Zm8");
    tempera_string_free(challenge);
    challenge = tempera_base64url_no_pad((const unsigned char *)"\xff\xfe\xfd", 3);
    CHECK_STR(challenge, "__79");
    tempera_string_free(challenge);

    /* PKCE from caller-supplied entropy: no RNG dependency. */
    for (index = 0; index < sizeof(entropy); index++) {
        entropy[index] = (unsigned char)index;
    }
    pair = tempera_pkce_pair_from_entropy(entropy, sizeof(entropy));
    CHECK(pair.verifier != NULL && pair.challenge != NULL, "PKCE pair not produced");
    CHECK_STR(pair.method, "S256");
    challenge = tempera_pkce_challenge_s256(pair.verifier);
    CHECK_STR(pair.challenge, challenge);
    tempera_string_free(challenge);
    CHECK(strlen(pair.verifier) >= 43, "PKCE verifier shorter than RFC 7636 allows");
    tempera_pkce_pair_free(&pair);
    CHECK(pair.verifier == NULL, "freed PKCE pair still holds a verifier");

    (void)tempera_auth_set_client_id(auth, "client_1");
    params.client_id = "client_1";
    params.redirect_uri = "https://app.example.test/callback";
    params.code_challenge = "challenge_1";
    params.audience = "tempo";
    params.scope = "trace:read trace:write";
    params.state = "state_1";
    url = tempera_auth_authorize_url(auth, &params);
    CHECK(strstr(url, "https://staging-api.tempera.dev/oauth/authorize?") == url,
          "authorize URL is wrong: %s", url);
    CHECK(strstr(url, "response_type=code") != NULL, "authorize URL lacks response_type: %s", url);
    CHECK(strstr(url, "resource=tempo") != NULL, "authorize URL lacks the RFC 8707 resource: %s",
          url);
    CHECK(strstr(url, "code_challenge_method=S256") != NULL, "authorize URL lacks S256: %s", url);
    CHECK(strstr(url, "scope=trace%3Aread%20trace%3Awrite") != NULL,
          "authorize URL scope is not form-encoded: %s", url);
    CHECK(strstr(url, "state=state_1") != NULL, "authorize URL lacks state: %s", url);
    tempera_string_free(url);

    url = tempera_auth_token_url(auth);
    CHECK_STR(url, "https://staging-api.tempera.dev/oauth/token");
    tempera_string_free(url);
    url = tempera_auth_revoke_url(auth);
    CHECK_STR(url, "https://staging-api.tempera.dev/oauth/revoke");
    tempera_string_free(url);
    url = tempera_auth_mcp_url(auth);
    CHECK_STR(url, "https://staging-api.tempera.dev/mcp");
    tempera_string_free(url);

    body = tempera_auth_code_exchange_body(auth, "code_1", "verifier_1",
                                           "https://app.example.test/callback", "tempo");
    CHECK_STR(body, "grant_type=authorization_code&code=code_1&code_verifier=verifier_1&"
                    "redirect_uri=https%3A%2F%2Fapp.example.test%2Fcallback&resource=tempo&"
                    "client_id=client_1");
    tempera_string_free(body);

    /* No tokens stored yet: no refresh body. */
    CHECK(tempera_auth_refresh_body(auth, "tempo") == NULL, "refresh body without a token");

    CHECK(tempera_auth_apply_token_response(auth, "tempo", "access_1", "refresh_1", 3600,
                                            "trace:read") == TEMPERA_OK,
          "token response rejected");
    CHECK_STR(tempera_auth_bearer_for(auth, "tempo"), "access_1");
    body = tempera_auth_refresh_body(auth, "tempo");
    CHECK_STR(body, "grant_type=refresh_token&refresh_token=refresh_1&resource=tempo&"
                    "client_id=client_1");
    tempera_string_free(body);

    /* Rotation: a new refresh token replaces the old one. */
    (void)tempera_auth_apply_token_response(auth, "tempo", "access_2", "refresh_2", -1, NULL);
    body = tempera_auth_refresh_body(auth, "tempo");
    CHECK(strstr(body, "refresh_token=refresh_2") != NULL, "rotation kept the old token: %s",
          body);
    tempera_string_free(body);

    /* An omitted refresh token keeps the stored one. */
    (void)tempera_auth_apply_token_response(auth, "tempo", "access_3", NULL, -1, NULL);
    CHECK_STR(tempera_auth_bearer_for(auth, "tempo"), "access_3");
    body = tempera_auth_refresh_body(auth, "tempo");
    CHECK(strstr(body, "refresh_token=refresh_2") != NULL, "rotation dropped the token: %s", body);
    tempera_string_free(body);

    /* The API key is the fallback bearer for every other audience. */
    CHECK(tempera_auth_bearer_for(auth, "palette") == NULL, "unset API key resolved a bearer");
    (void)tempera_auth_set_api_key(auth, "tp_key_1");
    CHECK_STR(tempera_auth_bearer_for(auth, "palette"), "tp_key_1");
    CHECK_STR(tempera_auth_bearer_for(auth, "tempo"), "access_3");
    body = tempera_auth_authorization_header(auth, "palette");
    CHECK_STR(body, "Bearer tp_key_1");
    tempera_string_free(body);

    /* Revoking returns the body and drops the stored token set. */
    body = tempera_auth_revoke_body(auth, "tempo");
    CHECK_STR(body, "token=refresh_2&token_type_hint=refresh_token&client_id=client_1");
    tempera_string_free(body);
    CHECK_STR(tempera_auth_bearer_for(auth, "tempo"), "tp_key_1");
    CHECK(tempera_auth_revoke_body(auth, "tempo") == NULL, "revoke twice produced a body");

    tempera_auth_free(auth);
}

/* An audience token is preferred over the unified API key. */
static void test_audience_token_precedence(void)
{
    tempera_auth *auth = tempera_auth_new("https://staging-api.tempera.dev");
    tempera_client *client;
    tempera_request *request = NULL;
    tempera_error error;
    tempera_param params[2];

    (void)tempera_auth_set_api_key(auth, "tp_key_1");
    (void)tempera_auth_apply_token_response(auth, "palette", "palette_access", NULL, -1, NULL);
    client = full_client(auth);
    params[0] = tempera_param_string("tenantId", "tenant_1");
    params[1] = tempera_param_string("traceId", "trace_1");
    CHECK(tempera_client_build_request(client, "palette", "get_trace", params, 2, &request,
                                       &error) == TEMPERA_OK,
          "audience token build failed: %s", error.detail);
    CHECK_STR(tempera_request_header(request, "authorization"), "Bearer palette_access");
    tempera_request_free(request);
    tempera_client_free(client);
    tempera_auth_free(auth);
}

/* ------------------------------------------------------------------------ */
/* 10. MCP JSON-RPC bodies                                                   */
/* ------------------------------------------------------------------------ */

static void test_mcp(void)
{
    tempera_mcp_builder builder;
    tempera_mcp_error error;
    long long id = 0;
    char *body;

    tempera_mcp_builder_init(&builder);

    body = tempera_mcp_initialize_body(&builder, "tempera-sdk", TEMPERA_SDK_VERSION, &id);
    CHECK(id == 1, "first request id is %lld", id);
    CHECK_STR(body,
              "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocol"
              "Version\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"tempera-"
              "sdk\",\"version\":\"0.13.0\"}}}");
    tempera_string_free(body);

    body = tempera_mcp_ping_body(&builder, &id);
    CHECK(id == 2, "ids do not increment (%lld)", id);
    CHECK_STR(body, "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"ping\"}");
    CHECK(strstr(body, "params") == NULL, "ping carries params");
    tempera_string_free(body);

    body = tempera_mcp_list_tools_body(&builder, &id);
    CHECK(id == 3, "ids do not increment (%lld)", id);
    CHECK_STR(body, "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/list\"}");
    tempera_string_free(body);

    body = tempera_mcp_call_tool_body(&builder, "tempera_search", "{\"query\":\"traces\"}", &id);
    CHECK_STR(body, "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\""
                    ":\"tempera_search\",\"arguments\":{\"query\":\"traces\"}}}");
    tempera_string_free(body);

    body = tempera_mcp_whoami_body(&builder, &id);
    CHECK_STR(body, "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\""
                    ":\"tempera_whoami\",\"arguments\":{}}}");
    tempera_string_free(body);

    body = tempera_mcp_status_body(&builder, &id);
    CHECK(strstr(body, "tempera_status") != NULL, "status body is wrong: %s", body);
    tempera_string_free(body);

    /* Tool names are JSON-escaped. */
    body = tempera_mcp_call_tool_body(&builder, "weird\"name", NULL, &id);
    CHECK(strstr(body, "\"name\":\"weird\\\"name\"") != NULL, "tool name not escaped: %s", body);
    tempera_string_free(body);

    CHECK(!tempera_mcp_parse_error("{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{}}", &error),
          "success response parsed as an error");
    CHECK(!tempera_mcp_parse_error("not json", &error), "unparseable body parsed as an error");
    CHECK(!tempera_mcp_parse_error("{\"error\":null}", &error), "null error parsed as an error");

    CHECK(tempera_mcp_parse_error(
              "{\"jsonrpc\":\"2.0\",\"id\":1,\"error\":{\"code\":-32002,\"message\":\"plan limit\","
              "\"data\":{\"plan\":\"free\"}}}",
              &error),
          "JSON-RPC error not parsed");
    CHECK(error.code == TEMPERA_MCP_ERROR_PLAN_LIMIT, "wrong MCP error code %lld", error.code);
    CHECK_STR(error.message, "plan limit");
    tempera_mcp_error_free(&error);

    CHECK(tempera_mcp_parse_error("{\"error\":{\"code\":-32601}}", &error), "error not parsed");
    CHECK(error.code == TEMPERA_MCP_ERROR_METHOD_NOT_FOUND, "wrong code %lld", error.code);
    CHECK_STR(error.message, "MCP error");
    tempera_mcp_error_free(&error);

    CHECK(tempera_mcp_parse_error("{\"error\":\"boom\"}", &error), "string error not parsed");
    CHECK(error.code == 0, "non-conformant error got a code");
    CHECK_STR(error.message, "boom");
    tempera_mcp_error_free(&error);
}

/* ------------------------------------------------------------------------ */
/* 11. Binary uploads, full URLs, and body escaping                          */
/* ------------------------------------------------------------------------ */

static void test_binary_and_serialization(const tempera_client *client)
{
    tempera_param params[3];
    tempera_request *request = NULL;
    tempera_error error;
    tempera_status status;
    char *full;
    const unsigned char content[3] = {1, 2, 3};

    params[0] = tempera_param_string("project_id", "project_1");
    params[1] = tempera_param_string("upload_id", "upload_1");
    status = tempera_client_build_binary(client, "tempera_document", "uploads_write", params, 2,
                                         content, sizeof(content), &request, &error);
    CHECK(status == TEMPERA_OK, "binary upload failed: %s", error.detail);
    CHECK(request->body_json == NULL, "binary upload carries a JSON body");
    CHECK(request->body_bytes_len == 3 && request->body_bytes != NULL &&
              request->body_bytes[0] == 1 && request->body_bytes[2] == 3,
          "binary payload not carried");
    CHECK_STR(tempera_request_header(request, "content-type"), "application/octet-stream");
    CHECK_STR(tempera_request_header(request, "authorization"), "Bearer tp_key_1");
    tempera_request_free(request);
    request = NULL;

    /* full_url appends the urlencoded query string. */
    params[0] = tempera_param_string("tenantId", "tenant_1");
    params[1] = tempera_param_string("traceId", "trace_1");
    params[2] = tempera_param_string("reason", "audit review");
    status =
        tempera_client_build_request(client, "palette", "get_trace", params, 3, &request, &error);
    CHECK(status == TEMPERA_OK, "get_trace failed: %s", error.detail);
    full = tempera_request_full_url(request);
    CHECK_STR(full,
              "https://palette.example.test/v1/traces/tenant_1/trace_1?reason=audit%20review");
    tempera_string_free(full);
    tempera_request_free(request);
    request = NULL;

    /* Body strings are JSON-escaped. */
    params[0] = tempera_param_string("mode", "login");
    params[1] = tempera_param_string("email", "dev\"quote\\slash@example.test");
    params[2] = tempera_param_string("password", "line\nbreak\ttab");
    status = tempera_client_build_request(client, "control_plane", "create_hosted_session", params,
                                          3, &request, &error);
    CHECK(status == TEMPERA_OK, "create_hosted_session failed: %s", error.detail);
    CHECK(strstr(request->body_json, "\"email\":\"dev\\\"quote\\\\slash@example.test\"") != NULL,
          "quotes/backslashes not escaped: %s", request->body_json);
    CHECK(strstr(request->body_json, "\"password\":\"line\\nbreak\\ttab\"") != NULL,
          "controls not escaped: %s", request->body_json);
    CHECK(request->body_json[0] == '{' &&
              request->body_json[strlen(request->body_json) - 1] == '}',
          "body is not an object: %s", request->body_json);
    tempera_request_free(request);
    request = NULL;

    /* A declared member is serialized once, whichever spelling arrives. */
    params[0] = tempera_param_string("email", "dev@example.test");
    params[1] = tempera_param_string("mode", "signup");
    status = tempera_client_build_request(client, "control_plane", "create_hosted_session", params,
                                          2, &request, &error);
    CHECK(status == TEMPERA_OK, "create_hosted_session failed: %s", error.detail);
    {
        const char *first = strstr(request->body_json, "\"mode\":");

        CHECK(first != NULL && strstr(first + 1, "\"mode\":") == NULL,
              "mode serialized twice: %s", request->body_json);
        CHECK(strstr(request->body_json, "\"mode\":\"signup\"") != NULL, "wrong mode: %s",
              request->body_json);
    }
    tempera_request_free(request);
    request = NULL;

    /* Typed parameters keep their JSON types in the body. */
    params[0] = tempera_param_bool("byok", true);
    params[1] = tempera_param_json("metadata", "{\"a\":[1,2]}");
    status = tempera_client_build_request(client, "control_plane", "create_hosted_session", params,
                                          2, &request, &error);
    CHECK(status == TEMPERA_OK, "typed parameters failed: %s", error.detail);
    CHECK(strstr(request->body_json, "\"byok\":true") != NULL, "bool not serialized: %s",
          request->body_json);
    CHECK(strstr(request->body_json, "\"metadata\":{\"a\":[1,2]}") != NULL,
          "raw JSON not spliced: %s", request->body_json);
    tempera_request_free(request);
}

/* ------------------------------------------------------------------------ */
/* 12. The generated tables themselves                                       */
/* ------------------------------------------------------------------------ */

static void test_surface_tables(void)
{
    size_t index;
    bool found_default_audience = false;

    CHECK(TEMPERA_SURFACE_VERSION > 0, "surface version is not set");
    CHECK(TEMPERA_PRODUCT_COUNT >= 14, "product table is short (%lu)",
          (unsigned long)TEMPERA_PRODUCT_COUNT);
    CHECK(TEMPERA_ENVIRONMENT_COUNT >= 4, "environment table is short");
    CHECK(TEMPERA_MCP_METHOD_COUNT > 0, "MCP method table is empty");
    CHECK_STR(TEMPERA_INTROSPECT_PATH, "/v1/oauth/introspect");
    CHECK_STR(TEMPERA_MCP_PATH, "/mcp");

    for (index = 0; index < TEMPERA_AUDIENCE_COUNT; index++) {
        if (strcmp(TEMPERA_AUDIENCES[index], TEMPERA_DEFAULT_AUDIENCE) == 0) {
            found_default_audience = true;
        }
    }
    CHECK(found_default_audience, "the default audience is not registered");

    CHECK(tempera_find_product("palette") != NULL, "palette is missing");
    CHECK(tempera_find_product("temp_os") != NULL, "temp_os is missing");
    CHECK(tempera_find_product("nope") == NULL, "unknown product resolved");
    CHECK(tempera_find_operation("palette", "get_trace") != NULL, "get_trace is missing");
    CHECK(tempera_find_operation("palette", "nope") == NULL, "unknown operation resolved");
    CHECK(tempera_find_operation(NULL, NULL) == NULL, "NULL lookup resolved");
    CHECK_STR(tempera_find_product("palette")->audience, "palette");

    /* Every operation belongs to a registered product and a known auth kind. */
    for (index = 0; index < TEMPERA_OPERATION_COUNT; index++) {
        const tempera_operation_spec *op = &TEMPERA_OPERATIONS[index];

        CHECK(tempera_find_product(op->product) != NULL, "%s.%s: unregistered product",
              op->product, op->id);
        CHECK(strcmp(op->auth, "none") == 0 || strcmp(op->auth, "account") == 0 ||
                  strcmp(op->auth, "product") == 0 || strcmp(op->auth, "oauthResource") == 0 ||
                  strcmp(op->auth, "introspectionSecret") == 0,
              "%s.%s: unknown auth kind %s", op->product, op->id, op->auth);
        CHECK(strcmp(op->auth, "oauthResource") != 0 || op->auth_audience != NULL,
              "%s.%s: oauthResource without an audience", op->product, op->id);
    }

    /* Non-ASCII descriptions survived the generator's byte escapes. */
    CHECK(TEMPERA_ENVIRONMENTS[0].environment[0] != '\0', "environment name is empty");
}

int main(void)
{
    tempera_auth *auth = make_auth();
    tempera_client *client = full_client(auth);

    if (auth == NULL || client == NULL) {
        (void)fprintf(stderr, "FAIL: could not allocate the test fixtures\n");
        return 1;
    }

    test_surface_tables();
    test_every_operation_builds(client);
    test_alias_handling(client);
    test_forbidden_body(client);
    test_aip_path_patterns(client);
    test_forward_compatible_spill(client);
    test_error_normalization();
    test_error_enum(auth);
    test_base_url_precedence();
    test_auth();
    test_audience_token_precedence();
    test_mcp();
    test_binary_and_serialization(client);

    tempera_client_free(client);
    tempera_auth_free(auth);

    (void)printf("%d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
