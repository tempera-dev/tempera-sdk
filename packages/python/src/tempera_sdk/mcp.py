"""Client for the unified Tempera MCP gateway (``${issuer}/mcp``).

The gateway implements the stateless MCP ``2026-07-28`` discovery lifecycle:
every POST carries the protocol/routing headers and complete client metadata,
and discovery uses ``server/discover`` rather than a stateful ``initialize``
exchange. Both JSON and streamable-HTTP SSE responses are supported.

Requires a bearer minted for audience ``tempera-mcp`` with scope ``mcp:invoke``
(or a central tp_ API key). Mirrors TemperaMcpClient in the TypeScript
package; the Rust crate exposes JSON-RPC body builders instead.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .auth import TemperaAuth, Transport, _default_transport, _encode_json
from .errors import (
    TemperaApiError,
    TemperaMcpError,
    TemperaMcpInputRequired,
    TemperaSdkError,
    _with_context,
)
from .surface import MCP_GATEWAY

MCP_PROTOCOL_VERSION = "2026-07-28"
MCP_PROTOCOL_VERSION_HEADER = "mcp-protocol-version"
MCP_METHOD_HEADER = "mcp-method"
MCP_NAME_HEADER = "mcp-name"

MCP_ERROR_CODES = dict(MCP_GATEWAY["errorCodes"])


def _routing_value_is_safe(value: str) -> bool:
    return bool(value) and all(0x21 <= ord(character) <= 0x7E for character in value)


def _decode_messages(payload: Any) -> list[Mapping[str, Any]]:
    """Normalize one JSON or SSE transport result into JSON-RPC messages."""
    if isinstance(payload, Mapping):
        return [payload]
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", "strict")
    if not isinstance(payload, str):
        raise TemperaSdkError("MCP response must be a JSON object or SSE text")

    text = payload.strip()
    if not text:
        return []
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        messages: list[Mapping[str, Any]] = []
        data_lines: list[str] = []

        def flush() -> None:
            if not data_lines:
                return
            try:
                candidate = json.loads("\n".join(data_lines))
            except json.JSONDecodeError as error:
                raise TemperaSdkError("MCP SSE response contains invalid JSON") from error
            data_lines.clear()
            if not isinstance(candidate, Mapping):
                raise TemperaSdkError("MCP SSE data must contain JSON-RPC objects")
            messages.append(candidate)

        for raw_line in text.replace("\r\n", "\n").split("\n"):
            if not raw_line:
                flush()
            elif raw_line.startswith("data:"):
                data_lines.append(raw_line[5:].lstrip(" "))
        flush()
        if not messages:
            raise TemperaSdkError("MCP response is neither JSON nor valid SSE")
        return messages
    if not isinstance(decoded, Mapping):
        raise TemperaSdkError("MCP JSON response must be an object")
    return [decoded]


def _result_object(result: Any, operation: str) -> Mapping[str, Any]:
    if not isinstance(result, Mapping):
        raise TemperaMcpError(
            f"MCP {operation} returned a non-object result", code=0, data=result
        )
    return result


def _complete_result(result: Any, operation: str) -> Mapping[str, Any]:
    value = _result_object(result, operation)
    if value.get("resultType") != "complete":
        raise TemperaMcpError(
            f"MCP {operation} did not return resultType complete",
            code=0,
            data=dict(value),
        )
    return value


def _input_requests_are_valid(value: Any) -> bool:
    allowed = {"sampling/createMessage", "elicitation/create", "roots/list"}
    if not isinstance(value, Mapping):
        return False
    for key, request in value.items():
        if not isinstance(key, str) or not isinstance(request, Mapping):
            return False
        method = request.get("method")
        params = request.get("params")
        if method not in allowed or (
            method == "roots/list"
            and params is not None
            and not isinstance(params, Mapping)
        ) or (
            method != "roots/list" and not isinstance(params, Mapping)
        ):
            return False
    return True


def _content_block_is_valid(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    if (
        ("_meta" in value and not isinstance(value["_meta"], Mapping))
        or ("annotations" in value and not isinstance(value["annotations"], Mapping))
    ):
        return False
    kind = value.get("type")
    if kind == "text":
        return isinstance(value.get("text"), str)
    if kind in {"image", "audio"}:
        return isinstance(value.get("data"), str) and isinstance(value.get("mimeType"), str)
    if kind == "resource_link":
        return isinstance(value.get("uri"), str) and isinstance(value.get("name"), str)
    if kind == "resource":
        resource = value.get("resource")
        return (
            isinstance(resource, Mapping)
            and isinstance(resource.get("uri"), str)
            and ("_meta" not in resource or isinstance(resource["_meta"], Mapping))
            and (
                isinstance(resource.get("text"), str)
                or isinstance(resource.get("blob"), str)
            )
        )
    return False


class TemperaMcpClient:
    """Stateless MCP 2026-07-28 client for the unified gateway."""

    def __init__(
        self,
        *,
        url: str | None = None,
        auth: TemperaAuth | None = None,
        bearer: str | None = None,
        transport: Transport | None = None,
        client_name: str = "tempera-sdk",
        client_version: str = "0.13.0",
        client_capabilities: Mapping[str, Any] | None = None,
    ):
        self.url = url or (auth.mcp_url if auth else None)
        if not self.url:
            raise TemperaSdkError("url is required (e.g. https://api.tempera.dev/mcp)")
        self.auth = auth
        self.bearer = bearer
        self.transport = transport or (auth.transport if auth else None) or _default_transport
        if not isinstance(client_name, str) or not client_name:
            raise TemperaSdkError("MCP client_name must be a non-empty string")
        if not isinstance(client_version, str) or not client_version:
            raise TemperaSdkError("MCP client_version must be a non-empty string")
        self.client_name = client_name
        self.client_version = client_version
        if client_capabilities is not None and (
            not isinstance(client_capabilities, Mapping) or client_capabilities
        ):
            raise TemperaSdkError(
                "MCP client_capabilities must stay empty until server-request handlers exist"
            )
        # A stateless HTTP response may contain server requests on its SSE
        # stream. Until this client exposes a dispatcher, advertising sampling,
        # elicitation, or any other client capability would be a false promise.
        self.client_capabilities: dict[str, Any] = {}
        self._next_id = 1

    def _resolve_bearer(self) -> str:
        bearer = self.bearer
        if not bearer and self.auth is not None:
            bearer = self.auth.bearer_for("tempera-mcp")
        if not bearer:
            raise TemperaSdkError("no MCP credential; pass bearer or a TemperaAuth with an api_key or tempera-mcp tokens")
        if not _routing_value_is_safe(bearer):
            raise TemperaSdkError("MCP bearer contains an unsafe header value")
        return bearer

    def _params(self, params: Mapping[str, Any] | None) -> dict[str, Any]:
        if params is not None and not isinstance(params, Mapping):
            raise TemperaSdkError("MCP params must be an object")
        enriched = dict(params or {})
        supplied_meta = enriched.get("_meta")
        if supplied_meta is not None and not isinstance(supplied_meta, Mapping):
            raise TemperaSdkError("MCP params._meta must be an object")
        enriched["_meta"] = {
            **dict(supplied_meta or {}),
            "io.modelcontextprotocol/protocolVersion": MCP_PROTOCOL_VERSION,
            "io.modelcontextprotocol/clientInfo": {
                "name": self.client_name,
                "version": self.client_version,
            },
            "io.modelcontextprotocol/clientCapabilities": {},
        }
        return enriched

    def rpc(self, method: str, params: Mapping[str, Any] | None = None) -> Any:
        """Send one stateless MCP request and return its correlated result."""
        if not isinstance(method, str) or not _routing_value_is_safe(method):
            raise TemperaSdkError("MCP method must be a non-empty safe routing value")
        request_id = self._next_id
        self._next_id += 1
        enriched = self._params(params)
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": enriched,
        }
        headers = {
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
            "authorization": f"Bearer {self._resolve_bearer()}",
            MCP_PROTOCOL_VERSION_HEADER: MCP_PROTOCOL_VERSION,
            MCP_METHOD_HEADER: method,
        }
        tool_name = enriched.get("name") if method == "tools/call" else None
        if method == "tools/call" and (
            not isinstance(tool_name, str) or not _routing_value_is_safe(tool_name)
        ):
            raise TemperaSdkError("MCP tool name must be a non-empty safe routing value")
        if isinstance(tool_name, str):
            headers[MCP_NAME_HEADER] = tool_name
        try:
            response = self.transport("POST", self.url, headers, _encode_json(payload))
        except TemperaApiError as error:
            raise _with_context(error, "mcpGateway", method) from None
        matches = [
            message
            for message in _decode_messages(response)
            if isinstance(message.get("id"), int)
            and not isinstance(message.get("id"), bool)
            and message.get("id") == request_id
            and "method" not in message
        ]
        if len(matches) != 1:
            raise TemperaSdkError(f"MCP {method} response omitted request id {request_id}")
        parsed = matches[0]
        if parsed.get("jsonrpc") != "2.0":
            raise TemperaSdkError(f"MCP {method} response has an invalid JSON-RPC version")
        has_result = "result" in parsed
        has_error = "error" in parsed
        if has_result == has_error:
            raise TemperaSdkError(
                f"MCP {method} response must contain exactly one of result or error"
            )
        if has_error:
            # A conformant JSON-RPC error requires an integer code and string
            # message. Ambiguous/non-object shapes fail as protocol errors.
            error = parsed["error"]
            if not isinstance(error, Mapping):
                raise TemperaSdkError(f"MCP {method} response has a malformed error object")
            code = error.get("code")
            message = error.get("message")
            if (
                not isinstance(code, int)
                or isinstance(code, bool)
                or not isinstance(message, str)
            ):
                raise TemperaSdkError(f"MCP {method} response has a malformed error object")
            raise TemperaMcpError(message, code=code, data=error.get("data"))
        return parsed["result"]

    def discover(self, *, name: str | None = None, version: str | None = None) -> Any:
        """Discover server capabilities using the stateless 2026-07-28 lifecycle."""
        if name is not None:
            if not isinstance(name, str) or not name:
                raise TemperaSdkError("MCP client name must be a non-empty string")
            self.client_name = name
        if version is not None:
            if not isinstance(version, str) or not version:
                raise TemperaSdkError("MCP client version must be a non-empty string")
            self.client_version = version
        result = _complete_result(self.rpc("server/discover", {}), "server/discover")
        supported = result.get("supportedVersions")
        capabilities = result.get("capabilities")
        ttl_ms = result.get("ttlMs")
        cache_scope = result.get("cacheScope")
        if (
            not isinstance(supported, list)
            or not all(isinstance(value, str) for value in supported)
            or MCP_PROTOCOL_VERSION not in supported
            or not isinstance(capabilities, Mapping)
            or not isinstance(ttl_ms, int)
            or isinstance(ttl_ms, bool)
            or ttl_ms < 0
            or cache_scope != "private"
            or ("instructions" in result and not isinstance(result["instructions"], str))
            or ("_meta" in result and not isinstance(result["_meta"], Mapping))
        ):
            raise TemperaMcpError(
                "MCP server/discover returned an incompatible result",
                code=0,
                data=dict(result),
            )
        return result

    def initialize(self, *, name: str = "tempera-sdk", version: str = "0.13.0") -> Any:
        """Compatibility alias for :meth:`discover`; no session is created."""
        return self.discover(name=name, version=version)

    def ping(self) -> Any:
        """Check gateway liveness over JSON-RPC."""
        return self.rpc("ping")

    def list_tools(self) -> list[Any]:
        """List every tool the gateway offers: builtins plus namespaced product tools."""
        result = _complete_result(self.rpc("tools/list"), "tools/list")
        tools = result.get("tools")
        if not isinstance(tools, list) or not all(
            isinstance(tool, Mapping) and isinstance(tool.get("name"), str)
            for tool in tools
        ):
            raise TemperaMcpError(
                "MCP tools/list returned an invalid tool catalog", code=0, data=dict(result)
            )
        return tools

    def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        input_responses: Mapping[str, Any] | None = None,
        request_state: str | None = None,
    ) -> Any:
        """Invoke a tool by name; product tool calls are metered as mcp_invocations."""
        if arguments is not None and not isinstance(arguments, Mapping):
            raise TemperaSdkError("MCP arguments must be an object")
        if input_responses is not None and not isinstance(input_responses, Mapping):
            raise TemperaSdkError("MCP input_responses must be an object")
        if request_state is not None and not isinstance(request_state, str):
            raise TemperaSdkError("MCP request_state must be a string")
        params: dict[str, Any] = {"name": name, "arguments": dict(arguments or {})}
        if input_responses is not None:
            params["inputResponses"] = dict(input_responses)
        if request_state is not None:
            params["requestState"] = request_state
        result = _result_object(self.rpc("tools/call", params), "tools/call")
        if result.get("resultType") == "input_required":
            input_requests = result.get("inputRequests")
            request_state = result.get("requestState")
            if (
                (input_requests is None and request_state is None)
                or (input_requests is not None and not _input_requests_are_valid(input_requests))
                or (request_state is not None and not isinstance(request_state, str))
            ):
                raise TemperaMcpError(
                    "MCP input_required result is malformed", code=0, data=dict(result)
                )
            raise TemperaMcpInputRequired(result)
        if result.get("resultType") != "complete":
            raise TemperaMcpError(
                "MCP tool returned an unsupported result type", code=0, data=dict(result)
            )
        known_fields = {"content", "structuredContent", "isError", "_meta"}
        if not known_fields.intersection(result):
            raise TemperaMcpError(
                "MCP tool returned an empty complete result", code=0, data=dict(result)
            )
        if (
            (
                "content" in result
                and (
                    not isinstance(result["content"], list)
                    or not all(_content_block_is_valid(block) for block in result["content"])
                )
            )
            or ("isError" in result and not isinstance(result["isError"], bool))
            or (
                "structuredContent" in result
                and not isinstance(result["structuredContent"], Mapping)
            )
            or ("_meta" in result and not isinstance(result["_meta"], Mapping))
        ):
            raise TemperaMcpError(
                "MCP tool returned a malformed complete result", code=0, data=dict(result)
            )
        if result.get("isError") is True:
            raise TemperaMcpError(
                "MCP tool reported an error outcome", code=0, data=dict(result)
            )
        return result

    def whoami(self) -> Any:
        """Fetch the caller's identity, workspace, and scopes as seen by the gateway."""
        return self.call_tool("tempera_whoami")

    def status(self) -> Any:
        """Fetch gateway upstream health for every connected product MCP server."""
        return self.call_tool("tempera_status")


__all__ = [
    "MCP_ERROR_CODES",
    "MCP_METHOD_HEADER",
    "MCP_NAME_HEADER",
    "MCP_PROTOCOL_VERSION",
    "MCP_PROTOCOL_VERSION_HEADER",
    "TemperaMcpClient",
]
