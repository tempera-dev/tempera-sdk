/**
 * Uniform Tempera SDK errors, shared in shape with the Python and Rust
 * packages (see surface.json `errorContract`).
 *
 * - `TemperaSdkError`: base class for every error the SDK throws, including
 *   configuration and usage mistakes (missing credential, unknown product).
 * - `TemperaApiError`: an HTTP response error, normalized from the canonical
 *   AIP-193 envelope and supported compatibility shapes so callers always read
 *   the same fields.
 * - `TemperaMcpError`: a JSON-RPC error from an MCP endpoint.
 */

export class TemperaSdkError extends Error {
  constructor(message, extra = {}) {
    super(message);
    this.name = "TemperaSdkError";
    // Back-compat: pre-0.2 callers read status/body off TemperaSdkError.
    if (extra.status !== undefined) this.status = extra.status;
    if (extra.body !== undefined) this.body = extra.body;
  }
}

export class TemperaApiError extends TemperaSdkError {
  constructor({ status, code, message, requestId, product, operation, body }) {
    super(message, { status, body });
    this.name = "TemperaApiError";
    this.status = status;
    this.code = code ?? null;
    this.requestId = requestId ?? null;
    this.product = product ?? null;
    this.operation = operation ?? null;
    this.body = body ?? null;
  }
}

export class TemperaMcpError extends TemperaSdkError {
  constructor({ code, message, data }) {
    super(message);
    this.name = "TemperaMcpError";
    this.code = code;
    this.data = data ?? null;
  }
}

/**
 * Normalize any Tempera product error body into {code, message, requestId}.
 *
 * Wire shapes handled (see surface.json errorContract.wireShapes):
 * - canonical resource API: {"error": {"code": 400, "status":
 *   "INVALID_ARGUMENT", "message": "...", "details": []}}
 * - legacy flat: {"error": "<code>", "message": "<text>"}
 * - legacy message-only: {"error": "<human message>"}
 * - legacy nested: {"error": {"code", "message", "request_id"?, ...}}
 */
export function normalizeErrorBody(body, statusText = "") {
  if (body && typeof body === "object") {
    const error = body.error;
    if (error && typeof error === "object") {
      return {
        code:
          typeof error.status === "string"
            ? error.status
            : typeof error.code === "string"
              ? error.code
              : null,
        message: typeof error.message === "string" ? error.message : statusText,
        requestId:
          typeof error.requestId === "string"
            ? error.requestId
            : typeof error.request_id === "string"
              ? error.request_id
              : null,
      };
    }
    if (typeof error === "string") {
      if (typeof body.message === "string") {
        return { code: error, message: body.message, requestId: null };
      }
      return { code: null, message: error, requestId: null };
    }
  }
  return { code: null, message: statusText || "request failed", requestId: null };
}

/**
 * Build a TemperaApiError from a failed HTTP response.
 * `requestId` falls back to the x-request-id response header.
 */
export function apiErrorFromResponse({ status, statusText, headers, body, product, operation }) {
  const normalized = normalizeErrorBody(body, statusText);
  const headerRequestId = headers?.get?.("x-request-id") ?? null;
  const label = [product, operation].filter(Boolean).join(".");
  return new TemperaApiError({
    status,
    code: normalized.code,
    message: `Tempera ${label || "request"} failed (${status}): ${normalized.message}`,
    requestId: normalized.requestId ?? headerRequestId,
    product,
    operation,
    body,
  });
}
