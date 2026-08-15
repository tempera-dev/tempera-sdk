"""tempera-sdk — the unified Tempera SDK for Python.

The package root intentionally exposes the complete public SDK while loading each ownership
module only when one of its symbols is requested. Provider-only processes therefore do not pay
for HTTP clients, OAuth, generated surfaces, or unrelated product code before their first MCP
request.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

# Public symbol -> (owning module, attribute). Keep this explicit so the package root remains a
# stable API contract without making every consumer import every product implementation.
_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    # generated surface
    "AUDIENCES": (".surface", "AUDIENCES"),
    "DEFAULT_AUDIENCE": (".surface", "DEFAULT_AUDIENCE"),
    "ENVIRONMENTS": (".surface", "ENVIRONMENTS"),
    "ISSUER_PATHS": (".surface", "ISSUER_PATHS"),
    "MCP_GATEWAY": (".surface", "MCP_GATEWAY"),
    "OPERATIONS": (".surface", "OPERATIONS"),
    "PRODUCTS": (".surface", "PRODUCTS"),
    "SCOPES": (".surface", "SCOPES"),
    "SURFACE_VERSION": (".surface", "SURFACE_VERSION"),
    # errors
    "TemperaApiError": (".errors", "TemperaApiError"),
    "TemperaMcpError": (".errors", "TemperaMcpError"),
    "TemperaSdkError": (".errors", "TemperaSdkError"),
    "api_error_from_response": (".errors", "api_error_from_response"),
    "normalize_error_body": (".errors", "normalize_error_body"),
    # auth
    "PRODUCT_AUDIENCES": (".auth", "PRODUCT_AUDIENCES"),
    "PkcePair": (".auth", "PkcePair"),
    "TemperaAuth": (".auth", "TemperaAuth"),
    "TokenSet": (".auth", "TokenSet"),
    "build_authorize_url": (".auth", "build_authorize_url"),
    "create_pkce_pair": (".auth", "create_pkce_pair"),
    "generate_pkce_verifier": (".auth", "generate_pkce_verifier"),
    "pkce_challenge_s256": (".auth", "pkce_challenge_s256"),
    # clients
    "TemperaClient": (".client", "TemperaClient"),
    "MCP_ERROR_CODES": (".mcp", "MCP_ERROR_CODES"),
    "MCP_PROTOCOL_VERSION": (".mcp", "MCP_PROTOCOL_VERSION"),
    "TemperaMcpClient": (".mcp", "TemperaMcpClient"),
    # provider authoring
    "MCP_PROVIDER_PROTOCOL_VERSION": (".provider", "MCP_PROVIDER_PROTOCOL_VERSION"),
    "ProviderArgumentError": (".provider", "ProviderArgumentError"),
    "ProviderDefinitionError": (".provider", "ProviderDefinitionError"),
    "TemperaProvider": (".provider_capabilities", "TemperaProvider"),
}

# Deprecated alias kept for 0.1.x callers; resolved lazily with ENVIRONMENTS.
_ALIAS_EXPORTS = {"API_TARGETS": "ENVIRONMENTS"}

__all__ = [
    "API_TARGETS",
    "AUDIENCES",
    "DEFAULT_AUDIENCE",
    "ENVIRONMENTS",
    "ISSUER_PATHS",
    "MCP_ERROR_CODES",
    "MCP_GATEWAY",
    "MCP_PROTOCOL_VERSION",
    "MCP_PROVIDER_PROTOCOL_VERSION",
    "OPERATIONS",
    "PRODUCTS",
    "PRODUCT_AUDIENCES",
    "PkcePair",
    "ProviderArgumentError",
    "ProviderDefinitionError",
    "SCOPES",
    "SURFACE_VERSION",
    "TemperaApiError",
    "TemperaAuth",
    "TemperaClient",
    "TemperaMcpClient",
    "TemperaMcpError",
    "TemperaProvider",
    "TemperaSdkError",
    "TokenSet",
    "api_error_from_response",
    "build_authorize_url",
    "create_pkce_pair",
    "generate_pkce_verifier",
    "normalize_error_body",
    "pkce_challenge_s256",
]


def __getattr__(name: str) -> Any:
    """Resolve one public root export and memoize it in the module namespace."""
    canonical = _ALIAS_EXPORTS.get(name, name)
    target = _LAZY_EXPORTS.get(canonical)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[canonical] = value
    if name != canonical:
        globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose the full stable root surface without eagerly importing its owners."""
    return sorted(set(globals()) | set(__all__))
