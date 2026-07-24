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

export const MCP_PROTOCOL_VERSION = "2025-06-18";

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
    const response = await this.fetch(this.url, {
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
        authorization: `Bearer ${this.#resolveBearer()}`,
      },
      body: JSON.stringify({ jsonrpc: "2.0", id: this.nextId++, method, ...(params !== undefined ? { params } : {}) }),
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

  /** Open an MCP session and fetch server capabilities and instructions. */
  initialize({ name = "tempera-sdk", version = "0.11.0" } = {}) {
    return this.rpc("initialize", {
      protocolVersion: MCP_PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: { name, version },
    });
  }

  /** Check gateway liveness over JSON-RPC. */
  ping() {
    return this.rpc("ping");
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
