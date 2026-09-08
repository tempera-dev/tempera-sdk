/*
 * Uniform Tempera API errors, shared in shape with the TypeScript, Python,
 * Rust, and C++ packages (see surface.json errorContract).
 *
 * Wire shapes handled:
 *   canonical resource API  {"error": {"code": 400, "status": "INVALID_ARGUMENT",
 *                                      "message": "...", "details": []}}
 *   legacy flat             {"error": "<code>", "message": "<text>"}
 *   legacy message-only     {"error": "<human message>"}
 *   legacy nested           {"error": {"code", "message", "request_id"?, ...}}
 *   anything unparseable    message is status_text, or "request failed" when
 *                           the status text is empty -- the same fallback rule
 *                           as every other package, so one wire response yields
 *                           one message everywhere.
 */

#include <stdlib.h>
#include <string.h>

#include "internal.h"

/* Copy a borrowed string, reporting allocation failure through `failed`. */
static char *dup_or_fail(const char *value, bool *failed)
{
    char *copy;

    if (value == NULL) {
        return NULL;
    }
    copy = tempera_strdup(value);
    if (copy == NULL) {
        *failed = true;
    }
    return copy;
}

/*
 * The AIP-193 google.rpc.ErrorInfo reason from an error's details[]. The first
 * detail carrying a string `reason` wins.
 */
static const char *error_info_reason(const tempera_json *error)
{
    const tempera_json *details = tempera_json_get(error, "details");
    size_t index;

    if (details == NULL || details->kind != TEMPERA_JSON_ARRAY) {
        return NULL;
    }
    for (index = 0; index < details->count; index++) {
        const char *reason = tempera_json_as_str(
            tempera_json_get(details->items[index], "reason"));

        if (reason != NULL) {
            return reason;
        }
    }
    return NULL;
}

void tempera_api_error_free(tempera_api_error *error)
{
    if (error == NULL) {
        return;
    }
    free(error->code);
    free(error->message);
    free(error->reason);
    free(error->request_id);
    error->code = NULL;
    error->message = NULL;
    error->reason = NULL;
    error->request_id = NULL;
    error->status = 0;
}

tempera_status tempera_normalize_error_body(int status,
                                            const char *status_text,
                                            const char *body,
                                            tempera_api_error *out_error)
{
    tempera_json *root;
    const tempera_json *error;
    bool failed = false;

    if (out_error == NULL) {
        return TEMPERA_ERR_INVALID_ARGUMENT;
    }
    memset(out_error, 0, sizeof(*out_error));
    out_error->status = status;
    if (status_text == NULL) {
        status_text = "";
    }

    root = tempera_json_parse(body);
    error = tempera_json_get(root, "error");
    if (error != NULL && error->kind == TEMPERA_JSON_OBJECT) {
        const char *code = tempera_json_as_str(tempera_json_get(error, "status"));
        const char *message = tempera_json_as_str(tempera_json_get(error, "message"));
        const char *request_id = tempera_json_as_str(tempera_json_get(error, "requestId"));

        if (code == NULL) {
            code = tempera_json_as_str(tempera_json_get(error, "code"));
        }
        if (request_id == NULL) {
            request_id = tempera_json_as_str(tempera_json_get(error, "request_id"));
        }
        out_error->code = dup_or_fail(code, &failed);
        out_error->message = dup_or_fail(message != NULL ? message : status_text, &failed);
        out_error->reason = dup_or_fail(error_info_reason(error), &failed);
        out_error->request_id = dup_or_fail(request_id, &failed);
    } else if (error != NULL && error->kind == TEMPERA_JSON_STRING) {
        const char *message = tempera_json_as_str(tempera_json_get(root, "message"));

        if (message != NULL) {
            out_error->code = dup_or_fail(error->text, &failed);
            out_error->message = dup_or_fail(message, &failed);
        } else {
            out_error->message = dup_or_fail(error->text, &failed);
        }
    } else {
        out_error->message =
            dup_or_fail(status_text[0] != '\0' ? status_text : "request failed", &failed);
    }
    tempera_json_free(root);

    if (failed) {
        tempera_api_error_free(out_error);
        return TEMPERA_ERR_OUT_OF_MEMORY;
    }
    return TEMPERA_OK;
}
