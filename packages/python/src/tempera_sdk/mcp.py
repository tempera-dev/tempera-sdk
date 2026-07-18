"""Client for the unified Tempera MCP gateway (``${issuer}/mcp``): stateless
streamable-HTTP JSON-RPC 2.0 aggregating every product MCP server behind
namespaced tools (palette_*, tempo_*, cradle_*, remi_*, data_engine_*).

Requires a bearer minted for audience ``tempera-mcp`` with scope ``mcp:invoke``
(or a central tp_ API key). Mirrors TemperaMcpClient in the TypeScript
package; the Rust crate exposes JSON-RPC body builders instead.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from .auth import TemperaAuth, Transport, _default_transport
from .errors import TemperaApiError, TemperaMcpError, TemperaSdkError, _with_context
from .surface import MCP_GATEWAY

MCP_PROTOCOL_VERSION = "2025-06-18"

MCP_ERROR_CODES = dict(MCP_GATEWAY["errorCodes"])


class TemperaMcpClient:
    """JSON-RPC client for the unified Tempera MCP gateway."""

    def __init__(
        self,
        *,
        url: str | None = None,
        auth: TemperaAuth | None = None,
        bearer: str | None = None,
        transport: Transport | None = None,
    ):
        self.url = url or (auth.mcp_url if auth else None)
        if not self.url:
            raise TemperaSdkError("url is required (e.g. https://api.tempera.dev/mcp)")
        self.auth = auth
        self.bearer = bearer
        self.transport = transport or (auth.transport if auth else None) or _default_transport
        self._next_id = 1

    def _resolve_bearer(self) -> str:
        if self.bearer:
            return self.bearer
        if self.auth is not None:
            return self.auth.bearer_for("tempera-mcp")
        raise TemperaSdkError("no MCP credential; pass bearer or a TemperaAuth with an api_key or tempera-mcp tokens")

    def rpc(self, method: str, params: Mapping[str, Any] | None = None) -> Any:
        """Send one JSON-RPC request and return its result (raises TemperaMcpError on rpc errors)."""
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        self._next_id += 1
        if params is not None:
            payload["params"] = dict(params)
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self._resolve_bearer()}",
        }
        try:
            parsed = self.transport("POST", self.url, headers, json.dumps(payload).encode("utf-8"))
        except TemperaApiError as error:
            raise _with_context(error, "mcpGateway", method) from None
        if isinstance(parsed, Mapping) and parsed.get("error"):
            # Uniform rule (same in TypeScript and Rust): a JSON-RPC error
            # object carries its integer code (0 when absent) and string
            # message; a non-conformant non-object error becomes code 0 with
            # its string form.
            error = parsed["error"]
            if isinstance(error, Mapping):
                code = error.get("code")
                message = error.get("message")
                raise TemperaMcpError(
                    message if isinstance(message, str) else "MCP error",
                    code=code if isinstance(code, int) and not isinstance(code, bool) else 0,
                    data=error.get("data"),
                )
            raise TemperaMcpError(str(error), code=0, data=None)
        return parsed.get("result") if isinstance(parsed, Mapping) else None

    def initialize(self, *, name: str = "tempera-sdk", version: str = "0.4.0") -> Any:
        """Open an MCP session and fetch server capabilities and instructions."""
        return self.rpc(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": name, "version": version},
            },
        )

    def ping(self) -> Any:
        """Check gateway liveness over JSON-RPC."""
        return self.rpc("ping")

    def list_tools(self) -> list[Any]:
        """List every tool the gateway offers: builtins plus namespaced product tools."""
        result = self.rpc("tools/list")
        if isinstance(result, Mapping):
            return result.get("tools") or []
        return []

    def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> Any:
        """Invoke a tool by name; product tool calls are metered as mcp_invocations."""
        return self.rpc("tools/call", {"name": name, "arguments": dict(arguments or {})})

    def whoami(self) -> Any:
        """Fetch the caller's identity, workspace, and scopes as seen by the gateway."""
        return self.call_tool("tempera_whoami")

    def status(self) -> Any:
        """Fetch gateway upstream health for every connected product MCP server."""
        return self.call_tool("tempera_status")


__all__ = ["MCP_ERROR_CODES", "MCP_PROTOCOL_VERSION", "TemperaMcpClient"]
