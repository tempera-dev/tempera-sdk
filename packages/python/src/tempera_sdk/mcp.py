"""Client for the unified Tempera MCP gateway (``${issuer}/mcp``): stateless
streamable-HTTP JSON-RPC 2.0 aggregating every product MCP server behind
namespaced tools (palette_*, tempo_*, cradle_*, remi_*, data_engine_*).

Requires a bearer minted for audience ``tempera-mcp`` with scope ``mcp:invoke``
(or a central tp_ API key). Mirrors TemperaMcpClient in the TypeScript
package; the Rust crate exposes JSON-RPC body builders instead.

``Transport`` returns an already-decoded JSON value. This client can validate
that decoded value, but cannot recover raw response bytes, parser depth, or
duplicate object keys that a transport parser already discarded.
"""

from __future__ import annotations

import json
import math
import threading
import unicodedata
from typing import Any, Mapping

from .auth import TemperaAuth, Transport, _default_transport, _encode_json
from .errors import TemperaApiError, TemperaMcpError, TemperaSdkError, _with_context
from .surface import MCP_GATEWAY

MCP_PROTOCOL_VERSION = "2026-07-28"

MCP_ERROR_CODES = dict(MCP_GATEWAY["errorCodes"])

# JavaScript's interoperable JSON-RPC integer range. Keeping request IDs in
# this range makes exact response correlation possible across SDKs.
_MAX_REQUEST_ID = 9_007_199_254_740_991
_MAX_TOOL_PAGES = 100
_MAX_TOOL_ITEMS = 10_000
_MAX_TOOL_PAGE_BYTES = 1 << 20
_MAX_TOOL_CATALOG_BYTES = 8 << 20
_MAX_JSON_DEPTH = 100
_MEASURE_CHUNK_CHARS = 8_192
_CATALOG_JSON_ENCODER = json.JSONEncoder(
    allow_nan=False,
    ensure_ascii=False,
    separators=(",", ":"),
)


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
        self._id_lock = threading.Lock()

    def _resolve_bearer(self) -> str:
        if self.bearer:
            return self.bearer
        if self.auth is not None:
            return self.auth.bearer_for("tempera-mcp")
        raise TemperaSdkError("no MCP credential; pass bearer or a TemperaAuth with an api_key or tempera-mcp tokens")

    def _allocate_request_id(self) -> int:
        """Return one unique interoperable request ID, without wrapping."""
        with self._id_lock:
            if self._next_id > _MAX_REQUEST_ID:
                raise TemperaSdkError("MCP request id limit reached")
            request_id = self._next_id
            self._next_id += 1
        return request_id

    @staticmethod
    def _protocol_error(message: str) -> None:
        raise TemperaSdkError(f"invalid MCP JSON-RPC response: {message}")

    def _send(self, method: str, params: Mapping[str, Any] | None) -> tuple[int, Any]:
        request_id = self._allocate_request_id()
        request_params = dict(params or {})
        meta = dict(request_params.get("_meta") or {})
        meta["io.modelcontextprotocol/protocolVersion"] = MCP_PROTOCOL_VERSION
        meta["io.modelcontextprotocol/clientCapabilities"] = {}
        request_params["_meta"] = meta
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": request_params,
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self._resolve_bearer()}",
            "mcp-protocol-version": MCP_PROTOCOL_VERSION,
            "mcp-method": method,
        }
        try:
            return request_id, self.transport("POST", self.url, headers, _encode_json(payload))
        except TemperaApiError as error:
            raise _with_context(error, "mcpGateway", method) from None

    def rpc(self, method: str, params: Mapping[str, Any] | None = None) -> Any:
        """Send one JSON-RPC request and return its result.

        A response must be a decoded JSON object with JSON-RPC 2.0, the exact
        integer request ID, and exactly one of ``result`` or ``error``.
        """
        request_id, response = self._send(method, params)
        if not isinstance(response, dict):
            self._protocol_error("response must be an object")
        if response.get("jsonrpc") != "2.0":
            self._protocol_error("jsonrpc must be exactly 2.0")
        if type(response.get("id")) is not int or response["id"] != request_id:
            self._protocol_error("response id does not match request id")

        has_result = "result" in response
        has_error = "error" in response
        if has_result == has_error:
            self._protocol_error("response must contain exactly one result or error")
        if has_result:
            # A present result is valid even when its JSON value is null.
            return response["result"]

        error = response["error"]
        if (
            not isinstance(error, dict)
            or type(error.get("code")) is not int
            or not isinstance(error.get("message"), str)
        ):
            self._protocol_error("malformed error")
        raise TemperaMcpError(error["message"], code=error["code"], data=error.get("data"))

    def initialize(self, *, name: str = "tempera-sdk", version: str = "0.12.0") -> Any:
        """Discover the stateless MCP server's capabilities and instructions."""
        return self.rpc(
            "server/discover",
            {
                "_meta": {
                    "io.modelcontextprotocol/clientInfo": {"name": name, "version": version},
                },
            },
        )

    def ping(self) -> Any:
        """Check gateway liveness over JSON-RPC."""
        return self.rpc("ping")

    @staticmethod
    def _validate_json_value(value: Any, byte_limit: int) -> None:
        """Validate with depth-sized state and a lower bound on encoded bytes.

        Iterators avoid copying wide objects/lists before the byte guard. The
        lower bound also rejects oversized strings before JSONEncoder creates
        an escaped fragment; the exact normalized count follows separately.
        """
        active_containers: set[int] = set()
        pending = [(iter((value,)), 0, None)]
        minimum_bytes = 0

        def charge(amount: int) -> None:
            nonlocal minimum_bytes
            minimum_bytes += amount
            if minimum_bytes > byte_limit:
                raise TemperaSdkError("invalid MCP JSON-RPC response: tools/list exceeds decoded catalog byte limit")

        def object_values(obj: dict[str, Any]):
            for key, child in obj.items():
                if not isinstance(key, str):
                    raise TemperaSdkError("invalid MCP catalog JSON: object key must be a string")
                charge(len(key) + 2)
                yield child

        while pending:
            iterator, depth, marker = pending[-1]
            try:
                current = next(iterator)
            except StopIteration:
                pending.pop()
                if marker is not None:
                    active_containers.remove(marker)
                continue

            if isinstance(current, str):
                charge(len(current) + 2)
                continue
            if current is None or isinstance(current, (bool, int)):
                charge(1)
                continue
            if isinstance(current, float):
                if not math.isfinite(current):
                    raise TemperaSdkError("invalid MCP catalog JSON: non-finite number")
                charge(1)
                continue
            if not isinstance(current, (dict, list)):
                raise TemperaSdkError("invalid MCP catalog JSON: unsupported value type")
            if depth >= _MAX_JSON_DEPTH:
                raise TemperaSdkError("invalid MCP catalog JSON: nesting exceeds depth limit")

            marker = id(current)
            if marker in active_containers:
                raise TemperaSdkError("invalid MCP catalog JSON: cycle")
            charge(2)
            active_containers.add(marker)
            children = object_values(current) if isinstance(current, dict) else iter(current)
            pending.append((children, depth + 1, marker))

    @classmethod
    def _bounded_json_bytes(cls, value: Any, limit: int) -> int:
        """Measure normalized JSON incrementally and stop as soon as it exceeds ``limit``."""
        cls._validate_json_value(value, limit)
        size = 0
        try:
            for fragment in _CATALOG_JSON_ENCODER.iterencode(value):
                for offset in range(0, len(fragment), _MEASURE_CHUNK_CHARS):
                    size += len(fragment[offset : offset + _MEASURE_CHUNK_CHARS].encode("utf-8"))
                    if size > limit:
                        cls._protocol_error("tools/list exceeds decoded catalog byte limit")
        except TemperaSdkError:
            raise
        except (TypeError, ValueError, OverflowError, RecursionError) as error:
            raise TemperaSdkError("invalid MCP catalog JSON") from error
        return size

    @classmethod
    def _validate_tool_descriptor(cls, tool: Any, names: set[str]) -> dict[str, Any]:
        if not isinstance(tool, dict):
            cls._protocol_error("tools/list tool must be an object")
        name = tool.get("name")
        if not isinstance(name, str) or not name:
            cls._protocol_error("tools/list tool must contain one non-empty name")
        if any(unicodedata.category(character) in {"Cc", "Cf"} for character in name):
            cls._protocol_error("tools/list tool name contains invisible character")
        if not isinstance(tool.get("inputSchema"), dict):
            cls._protocol_error("tools/list tool inputSchema must be a JSON object")
        if "description" in tool and not isinstance(tool["description"], str):
            cls._protocol_error("tools/list tool description must be a string")
        if name in names:
            cls._protocol_error(f"tools/list contains duplicate tool name {name}")
        names.add(name)
        return tool

    def list_tools(self) -> list[Any]:
        """List every validated tool across all bounded opaque-cursor pages."""
        tools: list[dict[str, Any]] = []
        names: set[str] = set()
        seen_cursors: set[str] = set()
        cursor: str | None = None
        total_bytes = 0

        for _ in range(_MAX_TOOL_PAGES):
            params = {"cursor": cursor} if cursor is not None else None
            result = self.rpc("tools/list", params)
            if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
                self._protocol_error("tools/list result must contain tools array")

            page_tools = result["tools"]
            # Check the item cap before traversing or encoding a page payload.
            if len(page_tools) > _MAX_TOOL_ITEMS - len(tools):
                self._protocol_error("tools/list exceeds item limit")

            page_limit = min(_MAX_TOOL_PAGE_BYTES, _MAX_TOOL_CATALOG_BYTES - total_bytes)
            page_bytes = self._bounded_json_bytes(result, page_limit)
            total_bytes += page_bytes

            for tool in page_tools:
                tools.append(self._validate_tool_descriptor(tool, names))

            if "nextCursor" not in result:
                return tools
            next_cursor = result["nextCursor"]
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
                self._protocol_error("tools/list repeated or invalid nextCursor")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

        self._protocol_error("tools/list exceeds page limit")

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
