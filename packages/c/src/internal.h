/*
 * Private helpers shared by the Tempera C runtime: a growable string buffer, a
 * couple of allocation helpers, and the minimal JSON scanner the error and MCP
 * modules use. Not installed and not part of the public ABI.
 */

#ifndef TEMPERA_INTERNAL_H
#define TEMPERA_INTERNAL_H

#include <stdbool.h>
#include <stddef.h>

#include "tempera/tempera.h"

/*
 * A growable, NUL-terminated string buffer. Appends never report failure
 * inline: an allocation failure latches `failed`, every later append is a
 * no-op, and tempera_buf_finish() returns NULL. That keeps the builders
 * readable without an error check on every append.
 */
typedef struct tempera_buf {
    char *data;
    size_t length;
    size_t capacity;
    bool failed;
} tempera_buf;

void tempera_buf_init(tempera_buf *buf);
void tempera_buf_append(tempera_buf *buf, const char *text);
void tempera_buf_append_bytes(tempera_buf *buf, const char *bytes, size_t length);
void tempera_buf_append_char(tempera_buf *buf, char value);
void tempera_buf_append_i64(tempera_buf *buf, long long value);
/* Transfer ownership of the buffer's storage; NULL when an append failed. */
char *tempera_buf_finish(tempera_buf *buf);
/* Release the buffer without transferring ownership. Accepts a zeroed buffer. */
void tempera_buf_dispose(tempera_buf *buf);

/* strdup()/strndup() are POSIX, not C99: carry our own. NULL in, NULL out. */
char *tempera_strdup(const char *value);
char *tempera_strndup(const char *value, size_t length);

/* Fill an optional out-parameter with a status and a formatted detail line. */
void tempera_error_set(tempera_error *out, tempera_status status, const char *format, ...);

/* ------------------------------------------------------------------------ */
/* Minimal JSON scanner                                                      */
/* ------------------------------------------------------------------------ */

typedef enum tempera_json_kind {
    TEMPERA_JSON_NULL = 0,
    TEMPERA_JSON_BOOL,
    TEMPERA_JSON_NUMBER,
    TEMPERA_JSON_STRING,
    TEMPERA_JSON_ARRAY,
    TEMPERA_JSON_OBJECT
} tempera_json_kind;

typedef struct tempera_json tempera_json;

struct tempera_json {
    tempera_json_kind kind;
    bool bool_value;
    /* STRING payload, or the raw source text of a NUMBER. */
    char *text;
    /* ARRAY elements, or OBJECT member values parallel to `keys`. */
    tempera_json **items;
    char **keys;
    size_t count;
};

/*
 * Parse a complete JSON document. Returns NULL on any syntax error or trailing
 * garbage, which callers treat as "unparseable body". Free with
 * tempera_json_free().
 */
tempera_json *tempera_json_parse(const char *input);
void tempera_json_free(tempera_json *value);

/* Member of an object by key; NULL for non-objects and missing keys. */
const tempera_json *tempera_json_get(const tempera_json *value, const char *key);
/* The string payload when this value is a JSON string, else NULL. */
const char *tempera_json_as_str(const tempera_json *value);
/* The integer payload when this value is a JSON number. */
bool tempera_json_as_i64(const tempera_json *value, long long *out);

#endif /* TEMPERA_INTERNAL_H */
