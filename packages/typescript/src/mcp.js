/** Stable Streamable HTTP client for the unified Tempera MCP gateway. */

import { TEMPERA_MCP_GATEWAY } from "./surface.js";
import { TemperaMcpError, TemperaSdkError, apiErrorFromResponse } from "./errors.js";

export const MCP_PROTOCOL_VERSION = "2025-11-25";

const ACCEPT = "application/json, text/event-stream";

function positiveInteger(value, name) {
  if (!Number.isSafeInteger(value) || value <= 0) throw new TemperaSdkError(`${name} must be a positive integer`);
  return value;
}

function nonNegativeInteger(value, name) {
  if (!Number.isSafeInteger(value) || value < 0) throw new TemperaSdkError(`${name} must be a non-negative integer`);
  return value;
}

function parseJson(text, context) {
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new TemperaSdkError(`invalid ${context} JSON: ${error.message}`);
  }
}

function parseSse(text) {
  const messages = [];
  let data = [];
  const flush = () => {
    if (data.length > 0) {
      const payload = data.join("\n");
      if (payload.trim()) messages.push(parseJson(payload, "MCP SSE event"));
      data = [];
    }
  };
  for (const line of text.replaceAll("\r\n", "\n").split("\n")) {
    if (line === "") {
      flush();
    } else if (line.startsWith("data:")) {
      data.push(line.slice(5).replace(/^ /, ""));
    }
  }
  flush();
  return messages;
}

function parseBody(text, contentType) {
  if (!text) return null;
  if (contentType.includes("text/event-stream")) return parseSse(text);
  return parseJson(text, "MCP response");
}

function rpcError(error) {
  const isObject = error !== null && typeof error === "object";
  return new TemperaMcpError({
    code: isObject && typeof error.code === "number" ? error.code : 0,
    message: isObject ? (typeof error.message === "string" ? error.message : "MCP error") : String(error),
    data: isObject ? error.data : null,
  });
}

export class TemperaMcpClient {
  constructor({
    url,
    auth,
    bearer,
    fetch: fetchImpl,
    protocolVersion = MCP_PROTOCOL_VERSION,
    timeoutMs = 120_000,
    maxPages = 100,
    maxItems = 10_000,
    autoInitialize = true,
    clientInfo = { name: "tempera-sdk", version: "0.4.0" },
  } = {}) {
    this.url = url ?? auth?.mcpUrl;
    if (!this.url) throw new TemperaSdkError("url is required (e.g. https://api.tempera.dev/mcp)");
    this.auth = auth ?? null;
    this.bearer = bearer ?? null;
    this.fetch = fetchImpl ?? auth?.fetch ?? globalThis.fetch;
    if (!this.fetch) throw new TemperaSdkError("fetch is required");
    this.protocolVersion = protocolVersion;
    this.timeoutMs = nonNegativeInteger(timeoutMs, "timeoutMs");
    this.maxPages = positiveInteger(maxPages, "maxPages");
    this.maxItems = positiveInteger(maxItems, "maxItems");
    this.autoInitialize = autoInitialize;
    this.clientInfo = clientInfo;
    this.nextId = 1;
    this.sessionId = null;
    this.serverInfo = null;
    this.initialized = false;
    this.initializePromise = null;
  }

  #resolveBearer() {
    if (this.bearer) return this.bearer;
    if (this.auth) return this.auth.bearerFor("tempera-mcp");
    throw new TemperaSdkError("no MCP credential; pass bearer or a TemperaAuth with an apiKey or tempera-mcp tokens");
  }

  #headers() {
    const headers = {
      accept: ACCEPT,
      "content-type": "application/json",
      authorization: `Bearer ${this.#resolveBearer()}`,
      "mcp-protocol-version": this.protocolVersion,
    };
    if (this.sessionId) headers["mcp-session-id"] = this.sessionId;
    return headers;
  }

  async #post(payload, operation, { signal, timeoutMs = this.timeoutMs, retrySession = true } = {}) {
    const controller = new AbortController();
    const onAbort = () => controller.abort(signal?.reason);
    if (signal) {
      if (signal.aborted) controller.abort(signal.reason);
      else signal.addEventListener("abort", onAbort, { once: true });
    }
    const timeout = timeoutMs > 0 ? setTimeout(() => controller.abort(new Error("MCP request timed out")), timeoutMs) : null;
    let response;
    let text;
    try {
      response = await this.fetch(this.url, {
        method: "POST",
        headers: this.#headers(),
        body: JSON.stringify(payload),
        redirect: "error",
        signal: controller.signal,
      });
      text = await response.text();
    } finally {
      if (timeout) clearTimeout(timeout);
      if (signal) signal.removeEventListener("abort", onAbort);
    }

    if (response.status === 404 && this.sessionId && retrySession && payload.method !== "initialize") {
      this.sessionId = null;
      this.initialized = false;
      await this.initialize(this.clientInfo, { signal, timeoutMs });
      return this.#post(payload, operation, { signal, timeoutMs, retrySession: false });
    }

    const contentType = response.headers.get("content-type") ?? "";
    const parsed = parseBody(text, contentType);
    if (!response.ok) {
      throw apiErrorFromResponse({
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
        body: Array.isArray(parsed) ? parsed.at(-1) : parsed,
        product: "mcpGateway",
        operation,
      });
    }
    return { response, messages: Array.isArray(parsed) ? parsed : parsed ? [parsed] : [] };
  }

  async #notify(method, params = undefined, options = {}) {
    const payload = { jsonrpc: "2.0", method, ...(params !== undefined ? { params } : {}) };
    await this.#post(payload, method, { ...options, retrySession: false });
  }

  async #cancel(id, reason) {
    try {
      await this.#notify("notifications/cancelled", { requestId: id, reason });
    } catch {
      // The original request still observes its own abort; cancellation is best effort on transport failure.
    }
  }

  /** Send one JSON-RPC request and return its validated result. */
  async rpc(method, params = undefined, { signal, timeoutMs } = {}) {
    const requestTimeout = timeoutMs === undefined ? this.timeoutMs : nonNegativeInteger(timeoutMs, "timeoutMs");
    if (this.autoInitialize && method !== "initialize" && !this.initialized) {
      await this.initialize(this.clientInfo, { signal, timeoutMs: requestTimeout });
    }
    if (signal?.aborted) throw signal.reason ?? new TemperaSdkError("MCP request aborted");
    const id = this.nextId++;
    let cancellationSent = false;
    const sendCancellation = (reason) => {
      if (!cancellationSent) {
        cancellationSent = true;
        void this.#cancel(id, reason);
      }
    };
    const onAbort = () => sendCancellation("caller aborted request");
    if (signal) signal.addEventListener("abort", onAbort, { once: true });
    const deadline = requestTimeout > 0
      ? setTimeout(() => sendCancellation("request deadline exceeded"), requestTimeout)
      : null;
    try {
      const payload = { jsonrpc: "2.0", id, method, ...(params !== undefined ? { params } : {}) };
      const { response, messages } = await this.#post(payload, method, { signal, timeoutMs: requestTimeout });
      const sessionId = response.headers.get("mcp-session-id");
      if (sessionId) this.sessionId = sessionId;
      const message = messages.find((candidate) => candidate?.id === id);
      if (!message) throw new TemperaSdkError(`MCP response did not contain JSON-RPC id ${id}`);
      if (message.jsonrpc !== "2.0") throw new TemperaSdkError("MCP response has an invalid jsonrpc version");
      if (Object.hasOwn(message, "error")) throw rpcError(message.error);
      if (!Object.hasOwn(message, "result")) throw new TemperaSdkError("MCP response has neither result nor error");
      return message.result;
    } finally {
      if (deadline) clearTimeout(deadline);
      if (signal) signal.removeEventListener("abort", onAbort);
    }
  }

  /** Initialize once, negotiate the stable protocol, then send notifications/initialized. */
  async initialize({ name = "tempera-sdk", version = "0.4.0" } = this.clientInfo, options = {}) {
    if (this.initialized) return this.serverInfo;
    if (this.initializePromise) return this.initializePromise;
    this.clientInfo = { name, version };
    this.initializePromise = (async () => {
      try {
        const requestedVersion = this.protocolVersion;
        const result = await this.rpc("initialize", {
          protocolVersion: requestedVersion,
          capabilities: {},
          clientInfo: this.clientInfo,
        }, options);
        if (result?.protocolVersion !== requestedVersion) {
          throw new TemperaSdkError(`MCP server did not negotiate supported protocol version ${requestedVersion}`);
        }
        this.serverInfo = result;
        await this.#notify("notifications/initialized", undefined, options);
        this.initialized = true;
        return result;
      } catch (error) {
        this.sessionId = null;
        this.serverInfo = null;
        this.initialized = false;
        throw error;
      }
    })();
    try {
      return await this.initializePromise;
    } finally {
      this.initializePromise = null;
    }
  }

  ping(options) {
    return this.rpc("ping", undefined, options);
  }

  async #listAll(method, key, { cursor: initialCursor, ...requestOptions } = {}) {
    const items = [];
    const seen = new Set();
    let cursor = initialCursor;
    for (let page = 0; page < this.maxPages; page += 1) {
      const result = await this.rpc(method, cursor ? { cursor } : undefined, requestOptions);
      const pageItems = result?.[key];
      if (!Array.isArray(pageItems)) throw new TemperaSdkError(`${method} returned an invalid ${key} collection`);
      if (items.length + pageItems.length > this.maxItems) {
        throw new TemperaSdkError(`${method} exceeded ${this.maxItems} items`);
      }
      items.push(...pageItems);
      const nextCursor = result?.nextCursor;
      if (nextCursor === undefined || nextCursor === null) return items;
      if (typeof nextCursor !== "string" || nextCursor.length === 0) {
        throw new TemperaSdkError(`${method} returned an invalid nextCursor`);
      }
      if (seen.has(nextCursor)) throw new TemperaSdkError(`${method} repeated a pagination cursor`);
      seen.add(nextCursor);
      cursor = nextCursor;
    }
    throw new TemperaSdkError(`${method} exceeded ${this.maxPages} pages`);
  }

  listTools(options) {
    return this.#listAll("tools/list", "tools", options);
  }

  callTool(name, args = {}, options) {
    return this.rpc("tools/call", { name, arguments: args }, options);
  }

  listResources(options) {
    return this.#listAll("resources/list", "resources", options);
  }

  readResource(uri, options) {
    return this.rpc("resources/read", { uri }, options);
  }

  listPrompts(options) {
    return this.#listAll("prompts/list", "prompts", options);
  }

  getPrompt(name, args = {}, options) {
    return this.rpc("prompts/get", { name, arguments: args }, options);
  }

  searchTools(query, { server, limit, includeSchema = false, ...options } = {}) {
    return this.callTool(
      "tempera_search_tools",
      { query, ...(server ? { server } : {}), ...(limit ? { limit } : {}), includeSchema },
      options,
    );
  }

  describeTool(name, options) {
    return this.callTool("tempera_describe_tool", { name }, options);
  }

  callDiscoveredTool(name, args = {}, options) {
    return this.callTool("tempera_call", { name, arguments: args }, options);
  }

  whoami(options) {
    return this.callTool("tempera_whoami", {}, options);
  }

  status(options) {
    return this.callTool("tempera_status", {}, options);
  }

  /** Close the stable MCP session. Safe to call more than once. */
  async close() {
    if (this.sessionId) {
      const controller = new AbortController();
      const timeout = this.timeoutMs > 0
        ? setTimeout(() => controller.abort(new Error("MCP session close timed out")), this.timeoutMs)
        : null;
      let response;
      let text = "";
      try {
        response = await this.fetch(this.url, {
          method: "DELETE",
          headers: this.#headers(),
          redirect: "error",
          signal: controller.signal,
        });
        if (!response.ok && response.status !== 404 && response.status !== 405) text = await response.text();
      } finally {
        if (timeout) clearTimeout(timeout);
      }
      if (!response.ok && response.status !== 404 && response.status !== 405) {
        throw apiErrorFromResponse({
          status: response.status,
          statusText: response.statusText,
          headers: response.headers,
          body: text ? parseBody(text, response.headers.get("content-type") ?? "") : null,
          product: "mcpGateway",
          operation: "session/delete",
        });
      }
    }
    this.sessionId = null;
    this.initialized = false;
    this.serverInfo = null;
  }
}

export const MCP_ERROR_CODES = Object.freeze(TEMPERA_MCP_GATEWAY.errorCodes);
