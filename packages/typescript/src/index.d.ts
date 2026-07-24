export * from "./surface.js";
export {
  TEMPERA_ENVIRONMENTS as TEMPERA_API_TARGETS,
  type TemperaEnvironmentTargets as TemperaApiTargets,
} from "./surface.js";

import type {
  ControlPlaneClient,
  CradleClient,
  DataEngineClient,
  PaletteClient,
  PassthroughClient,
  RemiClient,
  TemperaLlmClient,
  TemperaWorkflowsClient,
  TemperaGymClient,
  TemperaAudience,
  TemperaEnvironment,
  TemperaProductKey,
  TemperaScope,
  TempoClient,
} from "./surface.js";

// --- errors ---

export declare class TemperaSdkError extends Error {
  status?: number;
  body?: unknown;
}

export declare class TemperaApiError extends TemperaSdkError {
  status: number;
  code: string | null;
  requestId: string | null;
  product: string | null;
  operation: string | null;
  body: unknown;
}

export declare class TemperaMcpError extends TemperaSdkError {
  code: number;
  data: unknown;
}

export declare function normalizeErrorBody(
  body: unknown,
  statusText?: string,
): { code: string | null; message: string; requestId: string | null };

export declare function apiErrorFromResponse(options: {
  status: number;
  statusText?: string;
  headers?: { get(name: string): string | null };
  body?: unknown;
  product?: string;
  operation?: string;
}): TemperaApiError;

// --- auth ---

export declare function generatePkceVerifier(byteLength?: number): string;
export declare function pkceChallengeS256(verifier: string): Promise<string>;
export declare function createPkcePair(): Promise<{ verifier: string; challenge: string; method: "S256" }>;

export type TemperaAuthorizeUrlOptions = {
  issuerUrl: string;
  clientId: string;
  redirectUri: string;
  codeChallenge: string;
  audience?: TemperaAudience | (string & {});
  scope?: TemperaScope | (string & {}) | readonly (TemperaScope | (string & {}))[];
  state?: string;
};
export declare function buildAuthorizeUrl(options: TemperaAuthorizeUrlOptions): string;

export type TemperaTokenSet = {
  accessToken: string;
  refreshToken?: string;
  expiresIn?: number;
  scope?: string;
};

export type TemperaAuthOptions = {
  issuerUrl: string;
  clientId?: string;
  apiKey?: string;
  tokens?: Record<string, TemperaTokenSet>;
  fetch?: typeof fetch;
};

export declare class TemperaAuth {
  constructor(options: TemperaAuthOptions);
  issuerUrl: string;
  clientId?: string;
  apiKey?: string;
  tokens: Record<string, TemperaTokenSet>;
  fetch?: typeof fetch;
  get mcpUrl(): string;
  bearerFor(audience?: TemperaAudience | (string & {})): string;
  buildAuthorizeUrl(
    options: Omit<TemperaAuthorizeUrlOptions, "issuerUrl" | "clientId"> & { clientId?: string },
  ): string;
  exchangeCode(options: {
    code: string;
    codeVerifier: string;
    redirectUri: string;
    audience?: TemperaAudience | (string & {});
  }): Promise<TemperaTokenSet>;
  refresh(audience?: TemperaAudience | (string & {})): Promise<TemperaTokenSet>;
  revoke(
    audience?: TemperaAudience | (string & {}),
    options?: { tokenTypeHint?: "refresh_token" | "access_token" },
  ): Promise<void>;
}

export declare const TEMPERA_PRODUCT_AUDIENCES: Readonly<
  Partial<Record<TemperaProductKey, { audience: TemperaAudience; env: string }>>
>;

// --- unified client ---

export type TemperaClientOptions = {
  auth?: TemperaAuth;
  accountToken?: string;
  introspectionSecret?: string;
  baseUrls?: Partial<Record<TemperaProductKey, string>>;
  environment?: TemperaEnvironment;
  fetch?: typeof fetch;
};

export type TemperaClient = {
  auth: TemperaAuth | null;
  accountToken: string | null;
  controlPlane: ControlPlaneClient;
  palette: PaletteClient;
  tempo: TempoClient;
  temperaLlm: TemperaLlmClient;
  temperaWorkflows: TemperaWorkflowsClient;
  temperaGym: TemperaGymClient;
  temperaBio: TemperaBioClient;
  cradle: CradleClient;
  remi: RemiClient;
  dataEngine: DataEngineClient;
  humanData: HumanDataClient;
  tempJs: PassthroughClient;
  tempOS: PassthroughClient;
  arrha: PassthroughClient;
};

export declare function createTemperaClient(options?: TemperaClientOptions): TemperaClient;

// --- MCP gateway client ---

export declare const MCP_PROTOCOL_VERSION: string;
export declare const MCP_ERROR_CODES: Readonly<Record<string, number>>;

export type TemperaMcpClientOptions = {
  url?: string;
  auth?: TemperaAuth;
  bearer?: string;
  fetch?: typeof fetch;
};

export declare class TemperaMcpClient {
  constructor(options: TemperaMcpClientOptions);
  url: string;
  auth: TemperaAuth | null;
  bearer: string | null;
  rpc(method: string, params?: unknown): Promise<unknown>;
  initialize(clientInfo?: { name?: string; version?: string }): Promise<unknown>;
  ping(): Promise<unknown>;
  listTools(): Promise<unknown[]>;
  callTool(name: string, args?: Record<string, unknown>): Promise<unknown>;
  whoami(): Promise<unknown>;
  status(): Promise<unknown>;
}
