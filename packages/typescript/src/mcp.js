/**
 * Client for the unified Tempera MCP gateway (`${issuer}/mcp`): stateless
 * streamable-HTTP JSON-RPC 2.0 aggregating every product MCP server behind
 * namespaced tools (palette_*, tempo_*, cradle_*, remi_*, data_engine_*).
 *
 * Requires a bearer minted for audience `tempera-mcp` with scope `mcp:invoke`
 * (or a central tp_ API key). Mirrored by tempera_sdk.TemperaMcpClient in
 * Python; the Rust crate exposes JSON-RPC body builders instead.
 */

import { TEMPERA_MCP_GATEWAY } from "./surface.js";
import { TemperaMcpError, TemperaSdkError, apiErrorFromResponse } from "./errors.js";

export const MCP_PROTOCOL_VERSION = "2026-07-28";

// SEP-2243 routable headers. A middle box has to be able to route a request
// without parsing its body, so the method carries its subject in `Mcp-Name`:
// the tool for tools/call and prompts/get, the uri for the resources/* methods,
// the task id for the tasks/* ones. A gateway that validates them (tempera-mcp
// does) refuses a request that omits one.
const MCP_NAME_FROM = {
  "tools/call": "name",
  "prompts/get": "name",
  "resources/read": "uri",
  "resources/subscribe": "uri",
  "resources/unsubscribe": "uri",
  "tasks/get": "taskId",
  "tasks/update": "taskId",
  "tasks/cancel": "taskId",
};
const BASE64_HEADER_PREFIX = "=?base64?";
const BASE64_HEADER_SUFFIX = "?=";

/** A header value, Base64-wrapped when it could not survive as one. */
function headerSafe(value) {
  const unsafe =
    value.length > 0 &&
    (/^[ \t]|[ \t]$/.test(value) ||
      // eslint-disable-next-line no-control-regex
      /[^\x20-\x7e]/.test(value) ||
      (value.startsWith(BASE64_HEADER_PREFIX) && value.endsWith(BASE64_HEADER_SUFFIX)));
  if (!unsafe) return value;
  const encoded = Buffer.from(value, "utf8").toString("base64");
  return `${BASE64_HEADER_PREFIX}${encoded}${BASE64_HEADER_SUFFIX}`;
}

function mcpName(method, params) {
  const key = MCP_NAME_FROM[method];
  if (!key) return null;
  const value = params?.[key];
  return typeof value === "string" ? headerSafe(value) : null;
}

export class TemperaMcpClient {
  constructor({ url, auth, bearer, fetch: fetchImpl } = {}) {
    this.url = url ?? auth?.mcpUrl;
    if (!this.url) throw new TemperaSdkError("url is required (e.g. https://api.tempera.dev/mcp)");
    this.auth = auth ?? null;
    this.bearer = bearer ?? null;
    this.fetch = fetchImpl ?? auth?.fetch ?? globalThis.fetch;
    if (!this.fetch) throw new TemperaSdkError("fetch is required");
    this.nextId = 1;
  }

  #resolveBearer() {
    if (this.bearer) return this.bearer;
    if (this.auth) return this.auth.bearerFor("tempera-mcp");
    throw new TemperaSdkError("no MCP credential; pass bearer or a TemperaAuth with an apiKey or tempera-mcp tokens");
  }

  /** Send one JSON-RPC request and return its result (throws TemperaMcpError on rpc errors). */
  async rpc(method, params = undefined) {
    const requestMeta = {
      ...((params ?? {})._meta ?? {}),
        "io.modelcontextprotocol/protocolVersion": MCP_PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientCapabilities": {},
    };
    const requestParams = {
      ...(params ?? {}),
      _meta: requestMeta,
    };
    const response = await this.fetch(this.url, {
      method: "POST",
      headers: {
        // Streamable HTTP requires the client to accept BOTH shapes on a POST:
        // the gateway chooses one JSON body or an SSE stream, and a
        // spec-conformant gateway answers 406 to a client that offers only one.
        accept: "application/json, text/event-stream",
        "content-type": "application/json",
        authorization: `Bearer ${this.#resolveBearer()}`,
        "mcp-protocol-version": MCP_PROTOCOL_VERSION,
        "mcp-method": method,
        ...(mcpName(method, requestParams) === null
          ? {}
          : { "mcp-name": mcpName(method, requestParams) }),
      },
      body: JSON.stringify({ jsonrpc: "2.0", id: this.nextId++, method, params: requestParams }),
    });
    const text = await response.text();
    const parsed = text ? JSON.parse(text) : null;
    if (!response.ok) {
      throw apiErrorFromResponse({
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
        body: parsed,
        product: "mcpGateway",
        operation: method,
      });
    }
    if (parsed?.error) {
      // Uniform rule (same in Python and Rust): a JSON-RPC error object
      // carries its integer code (0 when absent) and string message; a
      // non-conformant non-object error becomes code 0 with its string form.
      const error = parsed.error;
      const isObject = typeof error === "object";
      throw new TemperaMcpError({
        code: isObject && typeof error.code === "number" ? error.code : 0,
        message: isObject ? (typeof error.message === "string" ? error.message : "MCP error") : String(error),
        data: isObject ? error.data : null,
      });
    }
    return parsed?.result;
  }

  /** Discover the stateless MCP server's capabilities and instructions. */
  initialize({ name = "tempera-sdk", version = "0.13.0" } = {}) {
    return this.rpc("server/discover", {
      _meta: { "io.modelcontextprotocol/clientInfo": { name, version } },
    });
  }

  /**
   * Check gateway liveness over JSON-RPC.
   *
   * @deprecated MCP revision 2026-07-28 removed `ping`; a gateway on that
   * revision answers it with a method-not-found. This helper now sends
   * `server/discover` so existing callers keep working, and will be removed
   * in a future release. Call `initialize()` instead.
   */
  ping() {
    return this.initialize();
  }

  /** List every tool the gateway offers: builtins plus namespaced product tools. */
  async listTools() {
    const result = await this.rpc("tools/list");
    return result?.tools ?? [];
  }

  /** Invoke a tool by name; product tool calls are metered as mcp_invocations. */
  callTool(name, args = {}) {
    return this.rpc("tools/call", { name, arguments: args });
  }

  /** Fetch the caller's identity, workspace, and scopes as seen by the gateway. */
  whoami() {
    return this.callTool("tempera_whoami");
  }

  /** Fetch gateway upstream health for every connected product MCP server. */
  status() {
    return this.callTool("tempera_status");
  }
}

export const MCP_ERROR_CODES = Object.freeze(TEMPERA_MCP_GATEWAY.errorCodes);
