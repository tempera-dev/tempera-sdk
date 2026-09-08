/* Growable buffers, allocation helpers, and the two public escaping helpers. */

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "internal.h"

void tempera_buf_init(tempera_buf *buf)
{
    buf->data = NULL;
    buf->length = 0;
    buf->capacity = 0;
    buf->failed = false;
}

static bool buf_reserve(tempera_buf *buf, size_t extra)
{
    size_t needed;
    size_t capacity;
    char *grown;

    if (buf->failed) {
        return false;
    }
    needed = buf->length + extra + 1;
    if (needed <= buf->capacity) {
        return true;
    }
    capacity = buf->capacity == 0 ? 64 : buf->capacity;
    while (capacity < needed) {
        capacity *= 2;
    }
    grown = (char *)realloc(buf->data, capacity);
    if (grown == NULL) {
        buf->failed = true;
        return false;
    }
    buf->data = grown;
    buf->capacity = capacity;
    return true;
}

void tempera_buf_append_bytes(tempera_buf *buf, const char *bytes, size_t length)
{
    if (bytes == NULL || length == 0) {
        /* Still make sure an empty buffer becomes a valid empty string. */
        if (buf_reserve(buf, 0) && buf->data != NULL) {
            buf->data[buf->length] = '\0';
        }
        return;
    }
    if (!buf_reserve(buf, length)) {
        return;
    }
    memcpy(buf->data + buf->length, bytes, length);
    buf->length += length;
    buf->data[buf->length] = '\0';
}

void tempera_buf_append(tempera_buf *buf, const char *text)
{
    if (text == NULL) {
        return;
    }
    tempera_buf_append_bytes(buf, text, strlen(text));
}

void tempera_buf_append_char(tempera_buf *buf, char value)
{
    tempera_buf_append_bytes(buf, &value, 1);
}

void tempera_buf_append_i64(tempera_buf *buf, long long value)
{
    char scratch[32];

    (void)snprintf(scratch, sizeof(scratch), "%lld", value);
    tempera_buf_append(buf, scratch);
}

char *tempera_buf_finish(tempera_buf *buf)
{
    char *data;

    if (buf->failed) {
        tempera_buf_dispose(buf);
        return NULL;
    }
    if (buf->data == NULL) {
        /* An empty buffer still owes the caller an empty string. */
        buf->data = (char *)malloc(1);
        if (buf->data == NULL) {
            return NULL;
        }
        buf->data[0] = '\0';
        buf->capacity = 1;
    }
    data = buf->data;
    tempera_buf_init(buf);
    return data;
}

void tempera_buf_dispose(tempera_buf *buf)
{
    free(buf->data);
    tempera_buf_init(buf);
}

char *tempera_strdup(const char *value)
{
    if (value == NULL) {
        return NULL;
    }
    return tempera_strndup(value, strlen(value));
}

char *tempera_strndup(const char *value, size_t length)
{
    char *copy;

    if (value == NULL) {
        return NULL;
    }
    copy = (char *)malloc(length + 1);
    if (copy == NULL) {
        return NULL;
    }
    memcpy(copy, value, length);
    copy[length] = '\0';
    return copy;
}

void tempera_error_set(tempera_error *out, tempera_status status, const char *format, ...)
{
    va_list args;

    if (out == NULL) {
        return;
    }
    out->status = status;
    out->detail[0] = '\0';
    if (format == NULL) {
        return;
    }
    va_start(args, format);
    (void)vsnprintf(out->detail, sizeof(out->detail), format, args);
    va_end(args);
}

void tempera_string_free(char *value)
{
    free(value);
}

const char *tempera_error_message(tempera_status status)
{
    switch (status) {
    case TEMPERA_OK:
        return "ok";
    case TEMPERA_ERR_UNKNOWN_OPERATION:
        return "unknown Tempera operation";
    case TEMPERA_ERR_MISSING_PATH_PARAM:
        return "missing required path parameter";
    case TEMPERA_ERR_MISSING_QUERY_PARAM:
        return "missing required query parameter";
    case TEMPERA_ERR_INVALID_PATH_PARAM:
        return "path parameter does not match its AIP resource pattern";
    case TEMPERA_ERR_FORBIDDEN_BODY_FIELD:
        return "parameter is derived from the authenticated principal";
    case TEMPERA_ERR_DUPLICATE_PARAMETER_ALIAS:
        return "pass either the wire name or its snake_case alias, not both";
    case TEMPERA_ERR_INVALID_IDEMPOTENCY_KEY:
        return "idempotency key must be 1-256 ASCII-graphic bytes";
    case TEMPERA_ERR_MISSING_ACCOUNT_TOKEN:
        return "an account token is required";
    case TEMPERA_ERR_MISSING_INTROSPECTION_SECRET:
        return "the introspection secret is required";
    case TEMPERA_ERR_MISSING_CREDENTIAL:
        return "no credential for the operation's token audience";
    case TEMPERA_ERR_INVALID_OPERATION_CONTRACT:
        return "generated operation contract is invalid for this call";
    case TEMPERA_ERR_MISSING_BASE_URL:
        return "missing base URL for the product";
    case TEMPERA_ERR_OUT_OF_MEMORY:
        return "out of memory";
    case TEMPERA_ERR_INVALID_ARGUMENT:
        return "invalid argument";
    }
    return "unknown Tempera status";
}

char *tempera_url_encode(const char *value)
{
    tempera_buf buf;
    size_t index;

    if (value == NULL) {
        return NULL;
    }
    tempera_buf_init(&buf);
    for (index = 0; value[index] != '\0'; index++) {
        unsigned char byte = (unsigned char)value[index];

        if ((byte >= 'A' && byte <= 'Z') || (byte >= 'a' && byte <= 'z') ||
            (byte >= '0' && byte <= '9') || byte == '-' || byte == '.' || byte == '_' ||
            byte == '~') {
            tempera_buf_append_char(&buf, (char)byte);
        } else {
            char escape[4];

            (void)snprintf(escape, sizeof(escape), "%%%02X", byte);
            tempera_buf_append(&buf, escape);
        }
    }
    return tempera_buf_finish(&buf);
}

char *tempera_json_escape(const char *value)
{
    tempera_buf buf;
    size_t index;

    if (value == NULL) {
        return NULL;
    }
    tempera_buf_init(&buf);
    for (index = 0; value[index] != '\0'; index++) {
        unsigned char byte = (unsigned char)value[index];

        switch (byte) {
        case '"':
            tempera_buf_append(&buf, "\\\"");
            break;
        case '\\':
            tempera_buf_append(&buf, "\\\\");
            break;
        case '\n':
            tempera_buf_append(&buf, "\\n");
            break;
        case '\r':
            tempera_buf_append(&buf, "\\r");
            break;
        case '\t':
            tempera_buf_append(&buf, "\\t");
            break;
        default:
            if (byte < 0x20) {
                char escape[8];

                (void)snprintf(escape, sizeof(escape), "\\u%04x", (unsigned int)byte);
                tempera_buf_append(&buf, escape);
            } else {
                tempera_buf_append_char(&buf, (char)byte);
            }
            break;
        }
    }
    return tempera_buf_finish(&buf);
}
