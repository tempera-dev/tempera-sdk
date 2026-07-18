"""tempera-sdk — the unified Tempera SDK for Python.

One credential set (a tp_ control-plane API key or per-audience OAuth
tokens), every product (control plane, palette, tempo, cradle, remi, and
passthrough clients for the rest), a uniform error model, and the unified
MCP gateway — with the same surface, operation names, and descriptions as
the TypeScript and Rust packages, generated from surface.json.
"""

from .surface import (
    AUDIENCES,
    DEFAULT_AUDIENCE,
    ENVIRONMENTS,
    ISSUER_PATHS,
    MCP_GATEWAY,
    OPERATIONS,
    PRODUCTS,
    SCOPES,
    SURFACE_VERSION,
)

from .errors import (
    TemperaApiError,
    TemperaMcpError,
    TemperaSdkError,
    api_error_from_response,
    normalize_error_body,
)

from .auth import (
    PRODUCT_AUDIENCES,
    PkcePair,
    TemperaAuth,
    TokenSet,
    build_authorize_url,
    create_pkce_pair,
    generate_pkce_verifier,
    pkce_challenge_s256,
)

from .client import RetryPolicy, TemperaClient

from .mcp import MCP_ERROR_CODES, MCP_PROTOCOL_VERSION, TemperaMcpClient

# Deprecated alias kept for 0.1.x callers; use ENVIRONMENTS.
API_TARGETS = ENVIRONMENTS

__all__ = [
    "API_TARGETS",
    "AUDIENCES",
    "DEFAULT_AUDIENCE",
    "ENVIRONMENTS",
    "ISSUER_PATHS",
    "MCP_ERROR_CODES",
    "MCP_GATEWAY",
    "MCP_PROTOCOL_VERSION",
    "OPERATIONS",
    "PRODUCTS",
    "PRODUCT_AUDIENCES",
    "PkcePair",
    "RetryPolicy",
    "SCOPES",
    "SURFACE_VERSION",
    "TemperaApiError",
    "TemperaAuth",
    "TemperaClient",
    "TemperaMcpClient",
    "TemperaMcpError",
    "TemperaSdkError",
    "TokenSet",
    "api_error_from_response",
    "build_authorize_url",
    "create_pkce_pair",
    "generate_pkce_verifier",
    "normalize_error_body",
    "pkce_challenge_s256",
]
