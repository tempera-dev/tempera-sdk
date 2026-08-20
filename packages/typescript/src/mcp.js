/**
 * Client for the unified Tempera MCP gateway (`${issuer}/mcp`).
 *
 * The gateway implements the stateless MCP 2026-07-28 discovery lifecycle:
 * every POST carries protocol/routing headers and complete client metadata,
 * and discovery uses `server/discover` rather than stateful `initialize`.
 *
 * Requires a bearer minted for audience `tempera-mcp` with scope `mcp:invoke`
 * (or a central tp_ API key). Mirrored by tempera_sdk.TemperaMcpClient in
 * Python; the Rust crate exposes JSON-RPC body builders instead.
 */

import { TEMPERA_MCP_GATEWAY } from "./surface.js";
import {
  TemperaMcpError,
  TemperaMcpInputRequired,
  TemperaSdkError,
  apiErrorFromResponse,
} from "./errors.js";

export const MCP_PROTOCOL_VERSION = "2026-07-28";
export const MCP_PROTOCOL_VERSION_HEADER = "mcp-protocol-version";
export const MCP_METHOD_HEADER = "mcp-method";
export const MCP_NAME_HEADER = "mcp-name";

function routingValueIsSafe(value) {
  return typeof value === "string" && value.length > 0 && /^[\x21-\x7e]+$/.test(value);
}

function decodeMessages(text, contentType) {
  if (!text) return [];
  if (!contentType.toLowerCase().includes("text/event-stream")) {
    const parsed = JSON.parse(text);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new TemperaSdkError("MCP JSON response must be an object");
    }
    return [parsed];
  }
  const messages = [];
  let data = [];
  const flush = () => {
    if (data.length === 0) return;
    const parsed = JSON.parse(data.join("\n"));
    data = [];
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new TemperaSdkError("MCP SSE data must contain JSON-RPC objects");
    }
    messages.push(parsed);
  };
  for (const line of text.replaceAll("\r\n", "\n").split("\n")) {
    if (!line) flush();
    else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
  }
  flush();
  if (messages.length === 0) throw new TemperaSdkError("MCP SSE response omitted JSON data");
  return messages;
}

function resultObject(result, operation) {
  if (!result || typeof result !== "object" || Array.isArray(result)) {
    throw new TemperaMcpError({ code: 0, message: `MCP ${operation} returned a non-object result`, data: result });
  }
  return result;
}

function completeResult(result, operation) {
  const value = resultObject(result, operation);
  if (value.resultType !== "complete") {
    throw new TemperaMcpError({
      code: 0,
      message: `MCP ${operation} did not return resultType complete`,
      data: value,
    });
  }
  return value;
}

function inputRequestsAreValid(value) {
  const allowed = new Set(["sampling/createMessage", "elicitation/create", "roots/list"]);
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  return Object.entries(value).every(([key, request]) => {
    const method = request?.method;
    const params = request?.params;
    return (
      typeof key === "string" &&
      request &&
      typeof request === "object" &&
      !Array.isArray(request) &&
      allowed.has(method) &&
      (method === "roots/list"
        ? params === undefined || (params && typeof params === "object" && !Array.isArray(params))
        : params && typeof params === "object" && !Array.isArray(params))
    );
  });
}

function contentBlockIsValid(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  if (
    (Object.hasOwn(value, "_meta") &&
      (!value._meta || typeof value._meta !== "object" || Array.isArray(value._meta))) ||
    (Object.hasOwn(value, "annotations") &&
      (!value.annotations || typeof value.annotations !== "object" || Array.isArray(value.annotations)))
  ) return false;
  if (value.type === "text") return typeof value.text === "string";
  if (value.type === "image" || value.type === "audio") {
    return typeof value.data === "string" && typeof value.mimeType === "string";
  }
  if (value.type === "resource_link") {
    return typeof value.uri === "string" && typeof value.name === "string";
  }
  if (value.type === "resource") {
    const resource = value.resource;
    return (
      resource &&
      typeof resource === "object" &&
      !Array.isArray(resource) &&
      typeof resource.uri === "string" &&
      (!Object.hasOwn(resource, "_meta") ||
        (resource._meta && typeof resource._meta === "object" && !Array.isArray(resource._meta))) &&
      (typeof resource.text === "string" || typeof resource.blob === "string")
    );
  }
  return false;
}

export class TemperaMcpClient {
  constructor({
    url,
    auth,
    bearer,
    fetch: fetchImpl,
    clientName = "tempera-sdk",
    clientVersion = "0.13.0",
    clientCapabilities = {},
  } = {}) {
    this.url = url ?? auth?.mcpUrl;
    if (!this.url) throw new TemperaSdkError("url is required (e.g. https://api.tempera.dev/mcp)");
    this.auth = auth ?? null;
    this.bearer = bearer ?? null;
    this.fetch = fetchImpl ?? auth?.fetch ?? globalThis.fetch;
    if (!this.fetch) throw new TemperaSdkError("fetch is required");
    if (typeof clientName !== "string" || clientName.length === 0) {
      throw new TemperaSdkError("MCP clientName must be a non-empty string");
    }
    if (typeof clientVersion !== "string" || clientVersion.length === 0) {
      throw new TemperaSdkError("MCP clientVersion must be a non-empty string");
    }
    this.clientName = clientName;
    this.clientVersion = clientVersion;
    if (
      !clientCapabilities ||
      typeof clientCapabilities !== "object" ||
      Array.isArray(clientCapabilities) ||
      Object.keys(clientCapabilities).length > 0
    ) {
      throw new TemperaSdkError(
        "MCP clientCapabilities must stay empty until server-request handlers exist",
      );
    }
    // Do not advertise sampling/elicitation/etc. until this stateless client
    // exposes a dispatcher for server requests arriving on the SSE stream.
    this.clientCapabilities = Object.freeze({});
    this.nextId = 1;
  }

  #resolveBearer() {
    const bearer = this.bearer || this.auth?.bearerFor("tempera-mcp");
    if (!bearer) {
      throw new TemperaSdkError("no MCP credential; pass bearer or a TemperaAuth with an apiKey or tempera-mcp tokens");
    }
    if (!routingValueIsSafe(bearer)) {
      throw new TemperaSdkError("MCP bearer contains an unsafe header value");
    }
    return bearer;
  }

  #params(params) {
    if (params !== undefined && (params === null || typeof params !== "object" || Array.isArray(params))) {
      throw new TemperaSdkError("MCP params must be an object");
    }
    const enriched = { ...(params ?? {}) };
    const suppliedMeta = enriched._meta;
    if (suppliedMeta !== undefined && (suppliedMeta === null || typeof suppliedMeta !== "object" || Array.isArray(suppliedMeta))) {
      throw new TemperaSdkError("MCP params._meta must be an object");
    }
    enriched._meta = {
      ...(suppliedMeta ?? {}),
      "io.modelcontextprotocol/protocolVersion": MCP_PROTOCOL_VERSION,
      "io.modelcontextprotocol/clientInfo": {
        name: this.clientName,
        version: this.clientVersion,
      },
      "io.modelcontextprotocol/clientCapabilities": {},
    };
    return enriched;
  }

  /** Send one stateless MCP request and return its correlated result. */
  async rpc(method, params = undefined) {
    if (!routingValueIsSafe(method)) {
      throw new TemperaSdkError("MCP method must be a non-empty safe routing value");
    }
    const id = this.nextId++;
    const enriched = this.#params(params);
    const headers = {
      accept: "application/json, text/event-stream",
      "content-type": "application/json",
      authorization: `Bearer ${this.#resolveBearer()}`,
      [MCP_PROTOCOL_VERSION_HEADER]: MCP_PROTOCOL_VERSION,
      [MCP_METHOD_HEADER]: method,
    };
    if (method === "tools/call") {
      if (!routingValueIsSafe(enriched.name)) {
        throw new TemperaSdkError("MCP tool name must be a non-empty safe routing value");
      }
      headers[MCP_NAME_HEADER] = enriched.name;
    }
    const response = await this.fetch(this.url, {
      method: "POST",
      headers,
      body: JSON.stringify({ jsonrpc: "2.0", id, method, params: enriched }),
    });
    const text = await response.text();
    let messages;
    try {
      messages = decodeMessages(text, response.headers.get("content-type") ?? "");
    } catch (error) {
      if (!response.ok) messages = [];
      else throw error;
    }
    const matches = messages.filter(
      (candidate) => candidate?.id === id && !Object.hasOwn(candidate, "method"),
    );
    const parsed = matches.length === 1 ? matches[0] : null;
    if (!response.ok) {
      throw apiErrorFromResponse({
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
        body: parsed ?? messages[0] ?? text,
        product: "mcpGateway",
        operation: method,
      });
    }
    if (!parsed) throw new TemperaSdkError(`MCP ${method} response omitted request id ${id}`);
    if (parsed.jsonrpc !== "2.0") {
      throw new TemperaSdkError(`MCP ${method} response has an invalid JSON-RPC version`);
    }
    const hasResult = Object.hasOwn(parsed, "result");
    const hasError = Object.hasOwn(parsed, "error");
    if (hasResult === hasError) {
      throw new TemperaSdkError(`MCP ${method} response must contain exactly one of result or error`);
    }
    if (hasError) {
      // A conformant JSON-RPC error requires an integer code and string
      // message. Ambiguous/non-object shapes fail as protocol errors.
      const error = parsed.error;
      const isObject = error && typeof error === "object" && !Array.isArray(error);
      if (!isObject || !Number.isSafeInteger(error.code) || typeof error.message !== "string") {
        throw new TemperaSdkError(`MCP ${method} response has a malformed error object`);
      }
      throw new TemperaMcpError({
        code: error.code,
        message: error.message,
        data: error.data,
      });
    }
    return parsed.result;
  }

  /** Discover capabilities using the stateless MCP 2026-07-28 lifecycle. */
  async discover({ name, version } = {}) {
    if (name !== undefined) {
      if (typeof name !== "string" || name.length === 0) {
        throw new TemperaSdkError("MCP client name must be a non-empty string");
      }
      this.clientName = name;
    }
    if (version !== undefined) {
      if (typeof version !== "string" || version.length === 0) {
        throw new TemperaSdkError("MCP client version must be a non-empty string");
      }
      this.clientVersion = version;
    }
    const result = completeResult(await this.rpc("server/discover", {}), "server/discover");
    const supported = result.supportedVersions;
    const capabilities = result.capabilities;
    const ttlMs = result.ttlMs;
    if (
      !Array.isArray(supported) ||
      !supported.every((value) => typeof value === "string") ||
      !supported.includes(MCP_PROTOCOL_VERSION) ||
      !capabilities ||
      typeof capabilities !== "object" ||
      Array.isArray(capabilities) ||
      !Number.isSafeInteger(ttlMs) ||
      ttlMs < 0 ||
      result.cacheScope !== "private" ||
      (Object.hasOwn(result, "instructions") && typeof result.instructions !== "string") ||
      (Object.hasOwn(result, "_meta") &&
        (!result._meta || typeof result._meta !== "object" || Array.isArray(result._meta)))
    ) {
      throw new TemperaMcpError({
        code: 0,
        message: "MCP server/discover returned an incompatible result",
        data: result,
      });
    }
    return result;
  }

  /** Compatibility alias for discover(); no transport session is created. */
  initialize({ name = "tempera-sdk", version = "0.13.0" } = {}) {
    return this.discover({ name, version });
  }

  /** Check gateway liveness over JSON-RPC. */
  ping() {
    return this.rpc("ping");
  }

  /** List every tool the gateway offers: builtins plus namespaced product tools. */
  async listTools() {
    const result = completeResult(await this.rpc("tools/list"), "tools/list");
    if (
      !Array.isArray(result.tools) ||
      !result.tools.every(
        (tool) => tool && typeof tool === "object" && !Array.isArray(tool) && typeof tool.name === "string",
      )
    ) {
      throw new TemperaMcpError({
        code: 0,
        message: "MCP tools/list returned an invalid tool catalog",
        data: result,
      });
    }
    return result.tools;
  }

  /** Invoke a tool by name; product tool calls are metered as mcp_invocations. */
  async callTool(name, args = {}, { inputResponses, requestState } = {}) {
    if (!args || typeof args !== "object" || Array.isArray(args)) {
      throw new TemperaSdkError("MCP arguments must be an object");
    }
    if (inputResponses !== undefined &&
      (!inputResponses || typeof inputResponses !== "object" || Array.isArray(inputResponses))) {
      throw new TemperaSdkError("MCP inputResponses must be an object");
    }
    if (requestState !== undefined && typeof requestState !== "string") {
      throw new TemperaSdkError("MCP requestState must be a string");
    }
    const params = { name, arguments: args };
    if (inputResponses !== undefined) params.inputResponses = inputResponses;
    if (requestState !== undefined) params.requestState = requestState;
    const result = resultObject(await this.rpc("tools/call", params), "tools/call");
    if (result.resultType === "input_required") {
      const inputRequests = result.inputRequests;
      const requestState = result.requestState;
      if (
        (inputRequests === undefined && requestState === undefined) ||
        (inputRequests !== undefined &&
          !inputRequestsAreValid(inputRequests)) ||
        (requestState !== undefined && typeof requestState !== "string")
      ) {
        throw new TemperaMcpError({
          code: 0,
          message: "MCP input_required result is malformed",
          data: result,
        });
      }
      throw new TemperaMcpInputRequired({ result });
    }
    if (result.resultType !== "complete") {
      throw new TemperaMcpError({
        code: 0,
        message: "MCP tool returned an unsupported result type",
        data: result,
      });
    }
    const knownFields = ["content", "structuredContent", "isError", "_meta"];
    if (!knownFields.some((field) => Object.hasOwn(result, field))) {
      throw new TemperaMcpError({ code: 0, message: "MCP tool returned an empty complete result", data: result });
    }
    if (
      (Object.hasOwn(result, "content") &&
        (!Array.isArray(result.content) || !result.content.every(contentBlockIsValid))) ||
      (Object.hasOwn(result, "structuredContent") &&
        (!result.structuredContent ||
          typeof result.structuredContent !== "object" ||
          Array.isArray(result.structuredContent))) ||
      (Object.hasOwn(result, "isError") && typeof result.isError !== "boolean") ||
      (Object.hasOwn(result, "_meta") &&
        (!result._meta || typeof result._meta !== "object" || Array.isArray(result._meta)))
    ) {
      throw new TemperaMcpError({ code: 0, message: "MCP tool returned a malformed complete result", data: result });
    }
    if (result.isError === true) {
      throw new TemperaMcpError({
        code: 0,
        message: "MCP tool reported an error outcome",
        data: result,
      });
    }
    return result;
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
