/*
 * A minimal JSON scanner, sufficient for the canonical AIP-193 error envelope,
 * the supported compatibility shapes, and JSON-RPC error objects. Ported from
 * the equally dependency-free scanner in packages/rust/src/error.rs, including
 * its strictness: raw control bytes inside strings, unpaired surrogates, and
 * trailing garbage all make the whole document unparseable.
 */

#include <stdlib.h>
#include <string.h>

#include "internal.h"

typedef struct parser {
    const unsigned char *bytes;
    size_t length;
    size_t position;
} parser;

static tempera_json *parse_value(parser *state);

static tempera_json *node_new(tempera_json_kind kind)
{
    tempera_json *node = (tempera_json *)calloc(1, sizeof(*node));

    if (node != NULL) {
        node->kind = kind;
    }
    return node;
}

void tempera_json_free(tempera_json *value)
{
    size_t index;

    if (value == NULL) {
        return;
    }
    for (index = 0; index < value->count; index++) {
        if (value->items != NULL) {
            tempera_json_free(value->items[index]);
        }
        if (value->keys != NULL) {
            free(value->keys[index]);
        }
    }
    free(value->items);
    free(value->keys);
    free(value->text);
    free(value);
}

/* Append one child (and, for objects, its key) to a container node. */
static bool node_push(tempera_json *node, char *key, tempera_json *child)
{
    tempera_json **items;

    items = (tempera_json **)realloc(node->items, (node->count + 1) * sizeof(*items));
    if (items == NULL) {
        return false;
    }
    node->items = items;
    if (key != NULL) {
        char **keys = (char **)realloc(node->keys, (node->count + 1) * sizeof(*keys));

        if (keys == NULL) {
            return false;
        }
        node->keys = keys;
        node->keys[node->count] = key;
    }
    node->items[node->count] = child;
    node->count++;
    return true;
}

static int peek(const parser *state)
{
    if (state->position >= state->length) {
        return -1;
    }
    return (int)state->bytes[state->position];
}

static int bump(parser *state)
{
    int byte = peek(state);

    if (byte >= 0) {
        state->position++;
    }
    return byte;
}

static void skip_whitespace(parser *state)
{
    for (;;) {
        int byte = peek(state);

        if (byte == ' ' || byte == '\t' || byte == '\n' || byte == '\r') {
            state->position++;
        } else {
            return;
        }
    }
}

static bool eat(parser *state, const char *token)
{
    size_t length = strlen(token);

    if (state->length - state->position < length) {
        return false;
    }
    if (memcmp(state->bytes + state->position, token, length) != 0) {
        return false;
    }
    state->position += length;
    return true;
}

static bool parse_hex4(parser *state, unsigned int *out)
{
    unsigned int value = 0;
    int index;

    for (index = 0; index < 4; index++) {
        int byte = bump(state);
        unsigned int digit;

        if (byte >= '0' && byte <= '9') {
            digit = (unsigned int)(byte - '0');
        } else if (byte >= 'a' && byte <= 'f') {
            digit = (unsigned int)(byte - 'a' + 10);
        } else if (byte >= 'A' && byte <= 'F') {
            digit = (unsigned int)(byte - 'A' + 10);
        } else {
            return false;
        }
        value = (value << 4) | digit;
    }
    *out = value;
    return true;
}

static void append_utf8(tempera_buf *buf, unsigned long code_point)
{
    if (code_point < 0x80UL) {
        tempera_buf_append_char(buf, (char)code_point);
    } else if (code_point < 0x800UL) {
        tempera_buf_append_char(buf, (char)(0xC0UL | (code_point >> 6)));
        tempera_buf_append_char(buf, (char)(0x80UL | (code_point & 0x3FUL)));
    } else if (code_point < 0x10000UL) {
        tempera_buf_append_char(buf, (char)(0xE0UL | (code_point >> 12)));
        tempera_buf_append_char(buf, (char)(0x80UL | ((code_point >> 6) & 0x3FUL)));
        tempera_buf_append_char(buf, (char)(0x80UL | (code_point & 0x3FUL)));
    } else {
        tempera_buf_append_char(buf, (char)(0xF0UL | (code_point >> 18)));
        tempera_buf_append_char(buf, (char)(0x80UL | ((code_point >> 12) & 0x3FUL)));
        tempera_buf_append_char(buf, (char)(0x80UL | ((code_point >> 6) & 0x3FUL)));
        tempera_buf_append_char(buf, (char)(0x80UL | (code_point & 0x3FUL)));
    }
}

/* Parse a JSON string body; returns owned decoded bytes, or NULL on error. */
static char *parse_string(parser *state)
{
    tempera_buf buf;

    tempera_buf_init(&buf);
    (void)bump(state); /* consume the opening quote */
    for (;;) {
        size_t start = state->position;
        int byte;

        while ((byte = peek(state)) >= 0) {
            if (byte == '"' || byte == '\\' || byte < 0x20) {
                break;
            }
            state->position++;
        }
        tempera_buf_append_bytes(&buf, (const char *)state->bytes + start,
                                 state->position - start);
        byte = bump(state);
        if (byte == '"') {
            char *finished = tempera_buf_finish(&buf);

            return finished;
        }
        if (byte != '\\') {
            /* End of input or a raw control character inside the string. */
            tempera_buf_dispose(&buf);
            return NULL;
        }
        byte = bump(state);
        switch (byte) {
        case '"':
            tempera_buf_append_char(&buf, '"');
            break;
        case '\\':
            tempera_buf_append_char(&buf, '\\');
            break;
        case '/':
            tempera_buf_append_char(&buf, '/');
            break;
        case 'b':
            tempera_buf_append_char(&buf, '\b');
            break;
        case 'f':
            tempera_buf_append_char(&buf, '\f');
            break;
        case 'n':
            tempera_buf_append_char(&buf, '\n');
            break;
        case 'r':
            tempera_buf_append_char(&buf, '\r');
            break;
        case 't':
            tempera_buf_append_char(&buf, '\t');
            break;
        case 'u': {
            unsigned int unit = 0;
            unsigned long code_point;

            if (!parse_hex4(state, &unit)) {
                tempera_buf_dispose(&buf);
                return NULL;
            }
            if (unit >= 0xD800U && unit < 0xDC00U) {
                unsigned int low = 0;

                if (bump(state) != '\\' || bump(state) != 'u' || !parse_hex4(state, &low) ||
                    low < 0xDC00U || low >= 0xE000U) {
                    tempera_buf_dispose(&buf);
                    return NULL;
                }
                code_point = 0x10000UL + (((unsigned long)unit - 0xD800UL) << 10) +
                             ((unsigned long)low - 0xDC00UL);
            } else if (unit >= 0xDC00U && unit < 0xE000U) {
                /* An unpaired low surrogate is not a code point. */
                tempera_buf_dispose(&buf);
                return NULL;
            } else {
                code_point = unit;
            }
            append_utf8(&buf, code_point);
            break;
        }
        default:
            tempera_buf_dispose(&buf);
            return NULL;
        }
    }
}

static bool eat_digits(parser *state)
{
    size_t start = state->position;

    while (peek(state) >= '0' && peek(state) <= '9') {
        state->position++;
    }
    return state->position > start;
}

static tempera_json *parse_number(parser *state)
{
    size_t start = state->position;
    tempera_json *node;

    if (peek(state) == '-') {
        state->position++;
    }
    if (!eat_digits(state)) {
        return NULL;
    }
    if (peek(state) == '.') {
        state->position++;
        if (!eat_digits(state)) {
            return NULL;
        }
    }
    if (peek(state) == 'e' || peek(state) == 'E') {
        state->position++;
        if (peek(state) == '+' || peek(state) == '-') {
            state->position++;
        }
        if (!eat_digits(state)) {
            return NULL;
        }
    }
    node = node_new(TEMPERA_JSON_NUMBER);
    if (node == NULL) {
        return NULL;
    }
    node->text = tempera_strndup((const char *)state->bytes + start, state->position - start);
    if (node->text == NULL) {
        tempera_json_free(node);
        return NULL;
    }
    return node;
}

static tempera_json *parse_object(parser *state)
{
    tempera_json *node = node_new(TEMPERA_JSON_OBJECT);

    if (node == NULL) {
        return NULL;
    }
    (void)bump(state); /* consume '{' */
    skip_whitespace(state);
    if (peek(state) == '}') {
        (void)bump(state);
        return node;
    }
    for (;;) {
        char *key;
        tempera_json *child;
        int byte;

        skip_whitespace(state);
        if (peek(state) != '"') {
            tempera_json_free(node);
            return NULL;
        }
        key = parse_string(state);
        if (key == NULL) {
            tempera_json_free(node);
            return NULL;
        }
        skip_whitespace(state);
        if (bump(state) != ':') {
            free(key);
            tempera_json_free(node);
            return NULL;
        }
        skip_whitespace(state);
        child = parse_value(state);
        if (child == NULL || !node_push(node, key, child)) {
            free(key);
            tempera_json_free(child);
            tempera_json_free(node);
            return NULL;
        }
        skip_whitespace(state);
        byte = bump(state);
        if (byte == ',') {
            continue;
        }
        if (byte == '}') {
            return node;
        }
        tempera_json_free(node);
        return NULL;
    }
}

static tempera_json *parse_array(parser *state)
{
    tempera_json *node = node_new(TEMPERA_JSON_ARRAY);

    if (node == NULL) {
        return NULL;
    }
    (void)bump(state); /* consume '[' */
    skip_whitespace(state);
    if (peek(state) == ']') {
        (void)bump(state);
        return node;
    }
    for (;;) {
        tempera_json *child;
        int byte;

        skip_whitespace(state);
        child = parse_value(state);
        if (child == NULL || !node_push(node, NULL, child)) {
            tempera_json_free(child);
            tempera_json_free(node);
            return NULL;
        }
        skip_whitespace(state);
        byte = bump(state);
        if (byte == ',') {
            continue;
        }
        if (byte == ']') {
            return node;
        }
        tempera_json_free(node);
        return NULL;
    }
}

static tempera_json *parse_value(parser *state)
{
    int byte = peek(state);
    tempera_json *node;

    switch (byte) {
    case '{':
        return parse_object(state);
    case '[':
        return parse_array(state);
    case '"': {
        char *text = parse_string(state);

        if (text == NULL) {
            return NULL;
        }
        node = node_new(TEMPERA_JSON_STRING);
        if (node == NULL) {
            free(text);
            return NULL;
        }
        node->text = text;
        return node;
    }
    case 't':
        if (!eat(state, "true")) {
            return NULL;
        }
        node = node_new(TEMPERA_JSON_BOOL);
        if (node != NULL) {
            node->bool_value = true;
        }
        return node;
    case 'f':
        if (!eat(state, "false")) {
            return NULL;
        }
        node = node_new(TEMPERA_JSON_BOOL);
        if (node != NULL) {
            node->bool_value = false;
        }
        return node;
    case 'n':
        if (!eat(state, "null")) {
            return NULL;
        }
        return node_new(TEMPERA_JSON_NULL);
    default:
        if (byte == '-' || (byte >= '0' && byte <= '9')) {
            return parse_number(state);
        }
        return NULL;
    }
}

tempera_json *tempera_json_parse(const char *input)
{
    parser state;
    tempera_json *value;

    if (input == NULL) {
        return NULL;
    }
    state.bytes = (const unsigned char *)input;
    state.length = strlen(input);
    state.position = 0;
    skip_whitespace(&state);
    value = parse_value(&state);
    if (value == NULL) {
        return NULL;
    }
    skip_whitespace(&state);
    if (state.position != state.length) {
        tempera_json_free(value);
        return NULL;
    }
    return value;
}

const tempera_json *tempera_json_get(const tempera_json *value, const char *key)
{
    size_t index;

    if (value == NULL || key == NULL || value->kind != TEMPERA_JSON_OBJECT) {
        return NULL;
    }
    for (index = 0; index < value->count; index++) {
        if (strcmp(value->keys[index], key) == 0) {
            return value->items[index];
        }
    }
    return NULL;
}

const char *tempera_json_as_str(const tempera_json *value)
{
    if (value == NULL || value->kind != TEMPERA_JSON_STRING) {
        return NULL;
    }
    return value->text;
}

bool tempera_json_as_i64(const tempera_json *value, long long *out)
{
    char *end = NULL;
    long long parsed;

    if (value == NULL || value->kind != TEMPERA_JSON_NUMBER || value->text == NULL) {
        return false;
    }
    parsed = strtoll(value->text, &end, 10);
    if (end != NULL && *end == '\0') {
        *out = parsed;
        return true;
    }
    /* Fall back to the floating-point reading, as the Rust scanner does. */
    {
        double approximate = strtod(value->text, &end);

        if (end == NULL || *end != '\0') {
            return false;
        }
        *out = (long long)approximate;
        return true;
    }
}
