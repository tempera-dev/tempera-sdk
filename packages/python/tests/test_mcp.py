import json
import unittest

from tempera_sdk import (
    MCP_ERROR_CODES,
    MCP_PROTOCOL_VERSION,
    TemperaApiError,
    TemperaAuth,
    TemperaMcpClient,
    TemperaMcpError,
    api_error_from_response,
)


class GatewayTransport:
    """Parses each JSON-RPC request and returns (or raises) the handler's value."""

    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def __call__(self, method, url, headers, data):
        request = json.loads(data)
        self.calls.append({"method": method, "url": url, "headers": headers, "data": data, "request": request})
        return self.handler(request)


def gateway_client(handler):
    transport = GatewayTransport(handler)
    client = TemperaMcpClient(url="https://api.tempera.dev/mcp", bearer="tp_key_1", transport=transport)
    return client, transport


class McpClientTest(unittest.TestCase):
    def test_initialize_ping_and_tools_list_send_well_formed_json_rpc(self):
        def handler(request):
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
            self.assertIsInstance(call["request"]["id"], int)
        self.assertEqual(transport.calls[0]["request"]["method"], "initialize")
        self.assertEqual(transport.calls[0]["request"]["params"]["protocolVersion"], "2025-06-18")
        self.assertEqual(MCP_PROTOCOL_VERSION, "2025-06-18")
        self.assertEqual(transport.calls[1]["request"]["method"], "ping")
        self.assertEqual(transport.calls[2]["request"]["method"], "tools/list")

    def test_json_rpc_request_bodies_use_the_compact_wire_shape(self):
        client, transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": {}}
        )
        client.ping()
        self.assertEqual(
            transport.calls[0]["data"],
            b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
        )

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


if __name__ == "__main__":
    unittest.main()


class NonConformantErrorTest(unittest.TestCase):
    def test_string_error_raises_tempera_mcp_error_with_code_0(self):
        client, _calls = gateway_client(lambda request: {"jsonrpc": "2.0", "id": 1, "error": "nope"})
        with self.assertRaises(TemperaMcpError) as caught:
            client.ping()
        self.assertEqual(caught.exception.code, 0)
        self.assertEqual(str(caught.exception), "nope")
