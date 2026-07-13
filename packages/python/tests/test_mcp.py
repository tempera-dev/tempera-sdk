import json
import unittest

from tempera_sdk import (
    MCP_ERROR_CODES,
    MCP_PROTOCOL_VERSION,
    TemperaApiError,
    TemperaAuth,
    TemperaMcpClient,
    TemperaMcpError,
    TemperaSdkError,
    api_error_from_response,
)
from tempera_sdk.mcp import _McpHttpResponse, _NoRedirectHandler


class GatewayTransport:
    """Parses each JSON-RPC request and returns (or raises) the handler's value."""

    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def __call__(self, method, url, headers, data):
        request = json.loads(data) if data else None
        self.calls.append({"method": method, "url": url, "headers": headers, "request": request})
        if request and "id" not in request:
            return None
        return self.handler(request)


def gateway_client(handler):
    transport = GatewayTransport(handler)
    client = TemperaMcpClient(
        url="https://api.tempera.dev/mcp",
        bearer="tp_key_1",
        transport=transport,
        auto_initialize=False,
    )
    return client, transport


class McpClientTest(unittest.TestCase):
    def test_initialize_ping_and_tools_list_send_well_formed_json_rpc(self):
        def handler(request):
            if request["method"] == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "serverInfo": {"name": "gateway", "version": "1"},
                    },
                }
            if request["method"] == "tools/list":
                return {"jsonrpc": "2.0", "id": request["id"], "result": {"tools": [{"name": "tempera_whoami"}]}}
            return {"jsonrpc": "2.0", "id": request["id"], "result": {}}

        client, transport = gateway_client(handler)
        client.initialize()
        client.ping()
        tools = client.list_tools()
        self.assertEqual(tools, [{"name": "tempera_whoami"}])
        for call in transport.calls:
            self.assertEqual(call["headers"]["authorization"], "Bearer tp_key_1")
            self.assertEqual(call["request"]["jsonrpc"], "2.0")
            self.assertEqual(call["headers"]["accept"], "application/json, text/event-stream")
        self.assertEqual(transport.calls[0]["request"]["method"], "initialize")
        self.assertEqual(transport.calls[0]["request"]["params"]["protocolVersion"], "2025-11-25")
        self.assertEqual(MCP_PROTOCOL_VERSION, "2025-11-25")
        self.assertEqual(transport.calls[1]["request"]["method"], "notifications/initialized")
        self.assertEqual(transport.calls[2]["request"]["method"], "ping")
        self.assertEqual(transport.calls[3]["request"]["method"], "tools/list")

    def test_initialize_rejects_unsupported_negotiated_protocol_version(self):
        client, transport = gateway_client(
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "protocolVersion": "2099-01-01",
                    "capabilities": {},
                    "serverInfo": {"name": "gateway", "version": "1"},
                },
            }
        )
        with self.assertRaisesRegex(TemperaSdkError, "did not negotiate supported protocol version"):
            client.initialize()
        self.assertEqual(len(transport.calls), 1)
        self.assertIsNone(client.session_id)
        self.assertFalse(client.initialized)

    def test_timeout_and_redirect_policy_fail_closed(self):
        with self.assertRaisesRegex(TemperaSdkError, "positive finite number"):
            TemperaMcpClient(url="https://api.tempera.dev/mcp", bearer="token", timeout=0)
        handler = _NoRedirectHandler()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "https://other.test/mcp"))

    def test_call_tool_whoami_and_status_wrap_tools_call(self):
        client, transport = gateway_client(
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"content": [{"type": "text", "text": "{}"}], "isError": False},
            }
        )
        client.call_tool("cradle_get_capabilities", {"verbose": True})
        client.whoami()
        client.status()
        self.assertEqual(transport.calls[0]["request"]["method"], "tools/call")
        self.assertEqual(
            transport.calls[0]["request"]["params"],
            {"name": "cradle_get_capabilities", "arguments": {"verbose": True}},
        )
        self.assertEqual(transport.calls[1]["request"]["params"]["name"], "tempera_whoami")
        self.assertEqual(transport.calls[2]["request"]["params"]["name"], "tempera_status")

    def test_json_rpc_errors_raise_tempera_mcp_error_with_code_and_data(self):
        client, _ = gateway_client(
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {
                    "code": MCP_ERROR_CODES["planLimit"],
                    "message": "Plan limit exceeded.",
                    "data": {"error": "plan_limit_exceeded"},
                },
            }
        )
        with self.assertRaises(TemperaMcpError) as ctx:
            client.call_tool("palette_list_traces")
        self.assertEqual(ctx.exception.code, -32002)
        self.assertEqual(ctx.exception.data, {"error": "plan_limit_exceeded"})

    def test_http_auth_failures_raise_tempera_api_error(self):
        def handler(request):
            raise api_error_from_response(
                401, "Unauthorized", {}, {"error": "unauthenticated", "message": "Bearer token required."}
            )

        client, _ = gateway_client(handler)
        with self.assertRaises(TemperaApiError) as ctx:
            client.ping()
        self.assertEqual(ctx.exception.status, 401)
        self.assertEqual(ctx.exception.code, "unauthenticated")
        self.assertEqual(ctx.exception.product, "mcpGateway")
        self.assertEqual(ctx.exception.operation, "ping")

    def test_the_gateway_url_derives_from_tempera_auth(self):
        auth = TemperaAuth(issuer_url="https://api.tempera.dev/", api_key="tp_key_1")
        client = TemperaMcpClient(auth=auth)
        self.assertEqual(client.url, "https://api.tempera.dev/mcp")

    def test_auto_initialize_preserves_session_and_parses_sse(self):
        calls = []

        def transport(method, url, headers, data):
            request = json.loads(data) if data else None
            calls.append({"method": method, "headers": headers, "request": request})
            if request["method"] == "initialize":
                body = "data: \nid: 0\nretry: 3000\n\ndata: " + json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "serverInfo": {"name": "gateway", "version": "1"},
                        },
                    }
                ) + "\n\n"
                return _McpHttpResponse(body, {"mcp-session-id": "session_1"})
            if request["method"] == "notifications/initialized":
                return _McpHttpResponse(None, {})
            body = "data: " + json.dumps(
                {"jsonrpc": "2.0", "id": request["id"], "result": {"tools": []}}
            ) + "\n\n"
            return _McpHttpResponse(body, {})

        client = TemperaMcpClient(
            url="https://api.tempera.dev/mcp",
            bearer="tp_key_1",
            transport=transport,
        )
        self.assertEqual(client.list_tools(), [])
        self.assertEqual(client.session_id, "session_1")
        self.assertEqual(calls[1]["headers"]["mcp-session-id"], "session_1")
        self.assertEqual(calls[2]["headers"]["mcp-protocol-version"], "2025-11-25")

    def test_pagination_and_progressive_discovery_helpers(self):
        def handler(request):
            if request["method"] == "tools/list":
                result = (
                    {"tools": [{"name": "second"}]}
                    if request.get("params", {}).get("cursor")
                    else {"tools": [{"name": "first"}], "nextCursor": "page-2"}
                )
            else:
                result = {"structuredContent": []}
            return {"jsonrpc": "2.0", "id": request["id"], "result": result}

        client, transport = gateway_client(handler)
        self.assertEqual(client.list_tools(), [{"name": "first"}, {"name": "second"}])
        client.search_tools("traces", server="palette", limit=3)
        client.describe_tool("palette_list_traces")
        client.call_discovered_tool("palette_list_traces", {"limit": 5})
        self.assertEqual(transport.calls[1]["request"]["params"], {"cursor": "page-2"})
        self.assertEqual(
            transport.calls[2]["request"]["params"]["arguments"],
            {"query": "traces", "server": "palette", "limit": 3, "includeSchema": False},
        )
        self.assertEqual(transport.calls[3]["request"]["params"]["name"], "tempera_describe_tool")
        self.assertEqual(transport.calls[4]["request"]["params"]["name"], "tempera_call")

    def test_pagination_enforces_item_bound(self):
        client = TemperaMcpClient(
            url="https://api.tempera.dev/mcp",
            bearer="tp_key_1",
            auto_initialize=False,
            max_items=1,
            transport=GatewayTransport(
                lambda request: {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {"tools": [{"name": "one"}, {"name": "two"}]},
                }
            ),
        )
        with self.assertRaisesRegex(TemperaSdkError, "tools/list exceeded 1 items"):
            client.list_tools()

    def test_pagination_rejects_malformed_cursor(self):
        client, _transport = gateway_client(
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"tools": [], "nextCursor": 42},
            }
        )
        with self.assertRaisesRegex(TemperaSdkError, "invalid nextCursor"):
            client.list_tools()

    def test_pagination_rejects_repeated_cursor(self):
        client, _transport = gateway_client(
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"tools": [], "nextCursor": "same"},
            }
        )
        with self.assertRaisesRegex(TemperaSdkError, "repeated a pagination cursor"):
            client.list_tools()


if __name__ == "__main__":
    unittest.main()


class NonConformantErrorTest(unittest.TestCase):
    def test_string_error_raises_tempera_mcp_error_with_code_0(self):
        client, _calls = gateway_client(lambda request: {"jsonrpc": "2.0", "id": 1, "error": "nope"})
        with self.assertRaises(TemperaMcpError) as caught:
            client.ping()
        self.assertEqual(caught.exception.code, 0)
        self.assertEqual(str(caught.exception), "nope")
