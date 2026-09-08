/*
 * JSON-RPC 2.0 body builders for the unified Tempera MCP gateway
 * (${issuer}/mcp): stateless streamable-HTTP JSON-RPC over the fixed
 * capability-fabric verb surface.
 *
 * The library is HTTP-less: these builders produce the exact request bodies the
 * gateway expects. POST them at tempera_auth_mcp_url() with an
 * "authorization: Bearer <token>" header (a bearer minted for audience
 * tempera-mcp with scope mcp:invoke, or a central tp_ API key), then feed error
 * responses to tempera_mcp_parse_error().
 */

#include <stdlib.h>
#include <string.h>

#include "internal.h"

void tempera_mcp_builder_init(tempera_mcp_builder *builder)
{
    if (builder != NULL) {
        builder->next_id = 1;
    }
}

static long long take_id(tempera_mcp_builder *builder, long long *out_id)
{
    long long id = builder->next_id;

    builder->next_id++;
    if (out_id != NULL) {
        *out_id = id;
    }
    return id;
}

/* "{"jsonrpc":"2.0","id":<id>,"method":"<method>"" -- no trailing brace. */
static void append_envelope(tempera_buf *buf, long long id, const char *method)
{
    tempera_buf_append(buf, "{\"jsonrpc\":\"2.0\",\"id\":");
    tempera_buf_append_i64(buf, id);
    tempera_buf_append(buf, ",\"method\":\"");
    tempera_buf_append(buf, method);
    tempera_buf_append_char(buf, '"');
}

static char *simple_body(tempera_mcp_builder *builder, const char *method, long long *out_id)
{
    tempera_buf buf;

    if (builder == NULL) {
        return NULL;
    }
    tempera_buf_init(&buf);
    append_envelope(&buf, take_id(builder, out_id), method);
    tempera_buf_append_char(&buf, '}');
    return tempera_buf_finish(&buf);
}

char *tempera_mcp_initialize_body(tempera_mcp_builder *builder,
                                  const char *client_name,
                                  const char *client_version,
                                  long long *out_id)
{
    tempera_buf buf;
    char *name;
    char *version;

    if (builder == NULL || client_name == NULL || client_version == NULL) {
        return NULL;
    }
    name = tempera_json_escape(client_name);
    version = tempera_json_escape(client_version);
    if (name == NULL || version == NULL) {
        tempera_string_free(name);
        tempera_string_free(version);
        return NULL;
    }
    tempera_buf_init(&buf);
    append_envelope(&buf, take_id(builder, out_id), "initialize");
    tempera_buf_append(&buf, ",\"params\":{\"protocolVersion\":\"");
    tempera_buf_append(&buf, TEMPERA_MCP_PROTOCOL_VERSION);
    tempera_buf_append(&buf, "\",\"capabilities\":{},\"clientInfo\":{\"name\":\"");
    tempera_buf_append(&buf, name);
    tempera_buf_append(&buf, "\",\"version\":\"");
    tempera_buf_append(&buf, version);
    tempera_buf_append(&buf, "\"}}}");
    tempera_string_free(name);
    tempera_string_free(version);
    return tempera_buf_finish(&buf);
}

char *tempera_mcp_ping_body(tempera_mcp_builder *builder, long long *out_id)
{
    return simple_body(builder, "ping", out_id);
}

char *tempera_mcp_list_tools_body(tempera_mcp_builder *builder, long long *out_id)
{
    return simple_body(builder, "tools/list", out_id);
}

char *tempera_mcp_call_tool_body(tempera_mcp_builder *builder,
                                 const char *tool_name,
                                 const char *arguments_json,
                                 long long *out_id)
{
    tempera_buf buf;
    char *name;

    if (builder == NULL || tool_name == NULL) {
        return NULL;
    }
    name = tempera_json_escape(tool_name);
    if (name == NULL) {
        return NULL;
    }
    tempera_buf_init(&buf);
    append_envelope(&buf, take_id(builder, out_id), "tools/call");
    tempera_buf_append(&buf, ",\"params\":{\"name\":\"");
    tempera_buf_append(&buf, name);
    tempera_buf_append(&buf, "\",\"arguments\":");
    tempera_buf_append(&buf, arguments_json != NULL ? arguments_json : "{}");
    tempera_buf_append(&buf, "}}");
    tempera_string_free(name);
    return tempera_buf_finish(&buf);
}

char *tempera_mcp_whoami_body(tempera_mcp_builder *builder, long long *out_id)
{
    return tempera_mcp_call_tool_body(builder, "tempera_whoami", NULL, out_id);
}

char *tempera_mcp_status_body(tempera_mcp_builder *builder, long long *out_id)
{
    return tempera_mcp_call_tool_body(builder, "tempera_status", NULL, out_id);
}

void tempera_mcp_error_free(tempera_mcp_error *error)
{
    if (error == NULL) {
        return;
    }
    free(error->message);
    error->message = NULL;
    error->code = 0;
}

bool tempera_mcp_parse_error(const char *body, tempera_mcp_error *out_error)
{
    tempera_json *root;
    const tempera_json *error;
    bool found = false;

    if (out_error == NULL) {
        return false;
    }
    memset(out_error, 0, sizeof(*out_error));
    root = tempera_json_parse(body);
    error = tempera_json_get(root, "error");
    if (error == NULL) {
        tempera_json_free(root);
        return false;
    }
    /*
     * Uniform rule (same in TypeScript, Python, and Rust): a JSON-RPC error
     * object carries its integer code (0 when absent) and string message; a
     * non-conformant non-object error becomes code 0 with its string form.
     */
    switch (error->kind) {
    case TEMPERA_JSON_OBJECT: {
        const char *message = tempera_json_as_str(tempera_json_get(error, "message"));
        long long code = 0;

        (void)tempera_json_as_i64(tempera_json_get(error, "code"), &code);
        out_error->code = code;
        out_error->message = tempera_strdup(message != NULL ? message : "MCP error");
        found = true;
        break;
    }
    case TEMPERA_JSON_STRING:
        out_error->message = tempera_strdup(error->text);
        found = true;
        break;
    case TEMPERA_JSON_NULL:
        found = false;
        break;
    case TEMPERA_JSON_NUMBER:
        out_error->message = tempera_strdup(error->text);
        found = true;
        break;
    case TEMPERA_JSON_BOOL:
        out_error->message = tempera_strdup(error->bool_value ? "true" : "false");
        found = true;
        break;
    case TEMPERA_JSON_ARRAY:
        out_error->message = tempera_strdup("");
        found = true;
        break;
    }
    tempera_json_free(root);
    if (found && out_error->message == NULL) {
        /* The only failure mode left is an allocation failure. */
        return false;
    }
    return found;
}
