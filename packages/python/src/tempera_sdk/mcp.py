"""Stable Streamable HTTP client for the unified Tempera MCP gateway."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Mapping
from urllib import error as urllib_error
from urllib import request as urllib_request

from .auth import TemperaAuth, Transport, _default_transport, _parse_body
from .errors import (
    TemperaApiError,
    TemperaMcpError,
    TemperaSdkError,
    _with_context,
    api_error_from_response,
)
from .surface import MCP_GATEWAY

MCP_PROTOCOL_VERSION = "2025-11-25"
MCP_ERROR_CODES = dict(MCP_GATEWAY["errorCodes"])

_ACCEPT = "application/json, text/event-stream"


def _positive_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TemperaSdkError(f"{name} must be a positive integer")
    return value


def _positive_number(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise TemperaSdkError(f"{name} must be a positive finite number")
    return float(value)


class _NoRedirectHandler(urllib_request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


_NO_REDIRECT_OPENER = urllib_request.build_opener(_NoRedirectHandler())


@dataclass(frozen=True)
class _McpHttpResponse:
    body: Any
    headers: Mapping[str, str]


def _parse_sse(text: str) -> list[Any]:
    messages: list[Any] = []
    data: list[str] = []

    def flush() -> None:
        if data:
            payload = "\n".join(data)
            data.clear()
            if not payload.strip():
                return
            try:
                messages.append(json.loads(payload))
            except ValueError as error:
                raise TemperaSdkError(f"invalid MCP SSE event JSON: {error}") from error

    for line in text.replace("\r\n", "\n").split("\n"):
        if not line:
            flush()
        elif line.startswith("data:"):
            value = line[5:]
            data.append(value[1:] if value.startswith(" ") else value)
    flush()
    return messages


def _messages(body: Any) -> list[Mapping[str, Any]]:
    if isinstance(body, str) and (body.startswith("data:") or "\ndata:" in body):
        body = _parse_sse(body)
    values = body if isinstance(body, list) else [body]
    return [value for value in values if isinstance(value, Mapping)]


class TemperaMcpClient:
    """Synchronous stable-protocol client with sessions, SSE, and pagination."""

    def __init__(
        self,
        *,
        url: str | None = None,
        auth: TemperaAuth | None = None,
        bearer: str | None = None,
        transport: Transport | None = None,
        protocol_version: str = MCP_PROTOCOL_VERSION,
        timeout: float = 120.0,
        max_pages: int = 100,
        max_items: int = 10_000,
        auto_initialize: bool = True,
        client_info: Mapping[str, str] | None = None,
    ):
        self.url = url or (auth.mcp_url if auth else None)
        if not self.url:
            raise TemperaSdkError("url is required (e.g. https://api.tempera.dev/mcp)")
        self.auth = auth
        self.bearer = bearer
        auth_transport = auth.transport if auth and auth.transport is not _default_transport else None
        self.transport = transport or auth_transport or self._default_mcp_transport
        self.protocol_version = protocol_version
        self.timeout = _positive_number(timeout, "timeout")
        self.max_pages = _positive_integer(max_pages, "max_pages")
        self.max_items = _positive_integer(max_items, "max_items")
        self.auto_initialize = auto_initialize
        self.client_info = dict(client_info or {"name": "tempera-sdk", "version": "0.4.0"})
        self.session_id: str | None = None
        self.server_info: Any = None
        self.initialized = False
        self._next_id = 1

    def _resolve_bearer(self) -> str:
        if self.bearer:
            return self.bearer
        if self.auth is not None:
            return self.auth.bearer_for("tempera-mcp")
        raise TemperaSdkError("no MCP credential; pass bearer or a TemperaAuth with an api_key or tempera-mcp tokens")

    def _headers(self) -> dict[str, str]:
        headers = {
            "accept": _ACCEPT,
            "content-type": "application/json",
            "authorization": f"Bearer {self._resolve_bearer()}",
            "mcp-protocol-version": self.protocol_version,
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        return headers

    def _default_mcp_transport(self, method: str, url: str, headers: dict[str, str], data: bytes | None) -> Any:
        req = urllib_request.Request(url, data=data, headers=headers, method=method)
        try:
            with _NO_REDIRECT_OPENER.open(req, timeout=self.timeout) as response:
                content_type = response.headers.get("content-type") or ""
                raw = response.read()
                body = raw.decode("utf-8", "replace") if "text/event-stream" in content_type else _parse_body(raw, content_type)
                return _McpHttpResponse(body, {key.lower(): value for key, value in response.headers.items()})
        except urllib_error.HTTPError as error:
            body = _parse_body(error.read(), error.headers.get("content-type") or "")
            raise api_error_from_response(error.code, error.reason or "", error.headers, body) from None

    def _send(self, payload: Mapping[str, Any], operation: str, *, retry_session: bool = True) -> tuple[list[Mapping[str, Any]], Mapping[str, str]]:
        try:
            response = self.transport("POST", self.url, self._headers(), json.dumps(payload).encode("utf-8"))
        except TemperaApiError as error:
            if error.status == 404 and self.session_id and retry_session and payload.get("method") != "initialize":
                self.session_id = None
                self.initialized = False
                self.initialize(**self.client_info)
                return self._send(payload, operation, retry_session=False)
            raise _with_context(error, "mcpGateway", operation) from None

        if isinstance(response, _McpHttpResponse):
            body = response.body
            headers = response.headers
        else:
            body = response
            headers = {}
        session_id = headers.get("mcp-session-id")
        if session_id:
            self.session_id = session_id
        return _messages(body), headers

    def _notify(self, method: str, params: Mapping[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = dict(params)
        self._send(payload, method, retry_session=False)

    def rpc(self, method: str, params: Mapping[str, Any] | None = None) -> Any:
        """Send one JSON-RPC request and return its validated result."""
        if self.auto_initialize and method != "initialize" and not self.initialized:
            self.initialize(**self.client_info)
        request_id = self._next_id
        self._next_id += 1
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = dict(params)
        messages, _headers = self._send(payload, method)
        response = next((message for message in messages if message.get("id") == request_id), None)
        if response is None:
            raise TemperaSdkError(f"MCP response did not contain JSON-RPC id {request_id}")
        if response.get("jsonrpc") != "2.0":
            raise TemperaSdkError("MCP response has an invalid jsonrpc version")
        if "error" in response:
            error = response["error"]
            if isinstance(error, Mapping):
                code = error.get("code")
                message = error.get("message")
                raise TemperaMcpError(
                    message if isinstance(message, str) else "MCP error",
                    code=code if isinstance(code, int) and not isinstance(code, bool) else 0,
                    data=error.get("data"),
                )
            raise TemperaMcpError(str(error), code=0, data=None)
        if "result" not in response:
            raise TemperaSdkError("MCP response has neither result nor error")
        return response["result"]

    def initialize(self, *, name: str = "tempera-sdk", version: str = "0.4.0") -> Any:
        """Negotiate the stable protocol and complete the MCP lifecycle."""
        if self.initialized:
            return self.server_info
        self.client_info = {"name": name, "version": version}
        requested_version = self.protocol_version
        try:
            result = self.rpc(
                "initialize",
                {
                    "protocolVersion": requested_version,
                    "capabilities": {},
                    "clientInfo": self.client_info,
                },
            )
            if not isinstance(result, Mapping) or result.get("protocolVersion") != requested_version:
                raise TemperaSdkError(
                    f"MCP server did not negotiate supported protocol version {requested_version}"
                )
            self.server_info = result
            self._notify("notifications/initialized")
        except Exception:
            self.session_id = None
            self.server_info = None
            self.initialized = False
            raise
        self.initialized = True
        return result

    def ping(self) -> Any:
        return self.rpc("ping")

    def _list_all(self, method: str, key: str, cursor: str | None = None) -> list[Any]:
        values: list[Any] = []
        seen: set[str] = set()
        for _page in range(self.max_pages):
            result = self.rpc(method, {"cursor": cursor} if cursor else None)
            if not isinstance(result, Mapping):
                raise TemperaSdkError(f"{method} returned an invalid result")
            page_values = result.get(key)
            if not isinstance(page_values, list):
                raise TemperaSdkError(f"{method} returned an invalid {key} collection")
            if len(values) + len(page_values) > self.max_items:
                raise TemperaSdkError(f"{method} exceeded {self.max_items} items")
            values.extend(page_values)
            next_cursor = result.get("nextCursor")
            if next_cursor is None:
                return values
            if not isinstance(next_cursor, str) or not next_cursor:
                raise TemperaSdkError(f"{method} returned an invalid nextCursor")
            if next_cursor in seen:
                raise TemperaSdkError(f"{method} repeated a pagination cursor")
            seen.add(next_cursor)
            cursor = next_cursor
        raise TemperaSdkError(f"{method} exceeded {self.max_pages} pages")

    def list_tools(self, *, cursor: str | None = None) -> list[Any]:
        return self._list_all("tools/list", "tools", cursor)

    def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> Any:
        return self.rpc("tools/call", {"name": name, "arguments": dict(arguments or {})})

    def list_resources(self, *, cursor: str | None = None) -> list[Any]:
        return self._list_all("resources/list", "resources", cursor)

    def read_resource(self, uri: str) -> Any:
        return self.rpc("resources/read", {"uri": uri})

    def list_prompts(self, *, cursor: str | None = None) -> list[Any]:
        return self._list_all("prompts/list", "prompts", cursor)

    def get_prompt(self, name: str, arguments: Mapping[str, Any] | None = None) -> Any:
        return self.rpc("prompts/get", {"name": name, "arguments": dict(arguments or {})})

    def search_tools(
        self,
        query: str,
        *,
        server: str | None = None,
        limit: int | None = None,
        include_schema: bool = False,
    ) -> Any:
        arguments: dict[str, Any] = {"query": query, "includeSchema": include_schema}
        if server:
            arguments["server"] = server
        if limit is not None:
            arguments["limit"] = limit
        return self.call_tool("tempera_search_tools", arguments)

    def describe_tool(self, name: str) -> Any:
        return self.call_tool("tempera_describe_tool", {"name": name})

    def call_discovered_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> Any:
        return self.call_tool("tempera_call", {"name": name, "arguments": dict(arguments or {})})

    def notify_cancelled(self, request_id: int | str, reason: str | None = None) -> None:
        params: dict[str, Any] = {"requestId": request_id}
        if reason:
            params["reason"] = reason
        self._notify("notifications/cancelled", params)

    def whoami(self) -> Any:
        return self.call_tool("tempera_whoami")

    def status(self) -> Any:
        return self.call_tool("tempera_status")

    def close(self) -> None:
        """Delete the current MCP session. Safe to call more than once."""
        if self.session_id:
            try:
                self.transport("DELETE", self.url, self._headers(), None)
            except TemperaApiError as error:
                if error.status not in {404, 405}:
                    raise _with_context(error, "mcpGateway", "session/delete") from None
        self.session_id = None
        self.server_info = None
        self.initialized = False


__all__ = ["MCP_ERROR_CODES", "MCP_PROTOCOL_VERSION", "TemperaMcpClient"]
