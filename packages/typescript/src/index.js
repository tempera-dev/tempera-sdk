/**
 * @tempera/sdk — the unified Tempera SDK for TypeScript.
 *
 * One credential set (a tp_ control-plane API key or per-audience OAuth
 * tokens), every product (control plane, palette, tempo, cradle, remi, and
 * passthrough clients for the rest), a uniform error model, and the unified
 * MCP gateway — with the same surface, operation names, and descriptions as
 * the Python and Rust packages, generated from surface.json.
 */

export {
  DEFAULT_AUDIENCE,
  TEMPERA_AUDIENCES,
  TEMPERA_ENVIRONMENTS,
  TEMPERA_ISSUER_PATHS,
  TEMPERA_MCP_GATEWAY,
  TEMPERA_OPERATIONS,
  TEMPERA_PRODUCTS,
  TEMPERA_SCOPES,
  TEMPERA_SURFACE_VERSION,
} from "./surface.js";

export {
  TemperaApiError,
  TemperaMcpError,
  TemperaSdkError,
  apiErrorFromResponse,
  normalizeErrorBody,
} from "./errors.js";

export {
  TEMPERA_PRODUCT_AUDIENCES,
  TemperaAuth,
  buildAuthorizeUrl,
  createPkcePair,
  generatePkceVerifier,
  pkceChallengeS256,
} from "./auth.js";

export { createTemperaClient } from "./client.js";

export { MCP_ERROR_CODES, MCP_PROTOCOL_VERSION, TemperaMcpClient } from "./mcp.js";

// Deprecated alias kept for 0.1.x callers; use TEMPERA_ENVIRONMENTS.
export { TEMPERA_ENVIRONMENTS as TEMPERA_API_TARGETS } from "./surface.js";
