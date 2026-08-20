import {
  MCP_PROTOCOL_VERSION,
  TemperaMcpClient,
  TemperaMcpError,
} from "../src/index.js";

const [endpoint, bearer, ...extra] = process.argv.slice(2);
if (!endpoint || !bearer || extra.length !== 0) {
  throw new Error("usage: node mcp_protocol_e2e.mjs <endpoint> <bearer>");
}

const expectedTools = [
  "tempera_capability_catalog",
  "tempera_children",
  "tempera_commit",
  "tempera_describe",
  "tempera_execute_plan",
  "tempera_invoke",
  "tempera_manage_connections",
  "tempera_prepare",
  "tempera_search",
  "tempera_status",
  "tempera_whoami",
];

const parsedEndpoint = new URL(endpoint);
if (
  parsedEndpoint.protocol !== "http:" ||
  parsedEndpoint.hostname !== "127.0.0.1" ||
  parsedEndpoint.port.length === 0 ||
  parsedEndpoint.pathname !== "/mcp" ||
  parsedEndpoint.username ||
  parsedEndpoint.password ||
  parsedEndpoint.search ||
  parsedEndpoint.hash
) {
  throw new Error("the TypeScript protocol E2E accepts only a disposable loopback /mcp URL");
}
if (bearer !== "local-e2e-placeholder") {
  throw new Error("the TypeScript protocol E2E accepts only its non-secret placeholder bearer");
}

const client = new TemperaMcpClient({
  url: endpoint,
  bearer,
  clientName: "tempera-sdk-typescript-e2e",
  clientVersion: "0.13.0",
});

const discovery = await client.discover();
if (
  discovery.resultType !== "complete" ||
  discovery.supportedVersions.length !== 1 ||
  discovery.supportedVersions[0] !== MCP_PROTOCOL_VERSION
) {
  throw new Error("server/discover did not return the exact supported protocol");
}

const tools = await client.listTools();
const actualTools = tools.map((tool) => tool.name).toSorted();
if (
  tools.length !== expectedTools.length ||
  JSON.stringify(actualTools) !== JSON.stringify(expectedTools)
) {
  throw new Error("tools/list did not return the exact fixed eleven-tool surface");
}

const identity = await client.whoami();
if (identity.isError === true || identity.structuredContent?.authenticated !== false) {
  throw new Error("tempera_whoami did not prove the protocol-only unauthenticated fixture");
}

let classifiedToolError = false;
try {
  await client.callTool("tempera_commit", {
    receipt: "typescript-secret-argument-sentinel",
  });
} catch (error) {
  if (
    !(error instanceof TemperaMcpError) ||
    error.code !== 0 ||
    error.data?.resultType !== "complete" ||
    error.data?.isError !== true
  ) {
    throw new Error("invalid tool arguments were not classified as a tool error");
  }
  classifiedToolError = true;
}
if (!classifiedToolError) {
  throw new Error("invalid tool arguments were reported as completed");
}

console.log("exact MCP 2026-07-28 TypeScript SDK E2E passed");
