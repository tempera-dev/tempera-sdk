import json
import unittest

from tempera_sdk import (
    MCP_ERROR_CODES,
    MCP_METHOD_HEADER,
    MCP_NAME_HEADER,
    MCP_PROTOCOL_VERSION,
    MCP_PROTOCOL_VERSION_HEADER,
    TemperaApiError,
    TemperaAuth,
    TemperaMcpClient,
    TemperaMcpError,
    TemperaMcpInputRequired,
    TemperaSdkError,
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


def discovery_result():
    return {
        "resultType": "complete",
        "supportedVersions": ["2026-07-28"],
        "capabilities": {"tools": {}},
        "ttlMs": 0,
        "cacheScope": "private",
    }


class McpClientTest(unittest.TestCase):
    def test_discovery_alias_and_every_request_use_the_stateless_protocol(self):
        def handler(request):
            if request["method"] == "tools/list":
                result = {"resultType": "complete", "tools": [{"name": "tempera_whoami"}]}
            elif request["method"] == "server/discover":
                result = discovery_result()
            else:
                result = {}
            return {"jsonrpc": "2.0", "id": request["id"], "result": result}

        client, transport = gateway_client(handler)
        discovery = client.initialize(name="tempera-voice", version="0.1.0")
        client.ping()
        tools = client.list_tools()
        self.assertEqual(discovery, discovery_result())
        self.assertEqual(tools, [{"name": "tempera_whoami"}])
        for call in transport.calls:
            self.assertEqual(call["headers"]["authorization"], "Bearer tp_key_1")
            self.assertEqual(
                call["headers"][MCP_PROTOCOL_VERSION_HEADER], MCP_PROTOCOL_VERSION
            )
            self.assertEqual(call["headers"][MCP_METHOD_HEADER], call["request"]["method"])
            self.assertEqual(call["headers"]["accept"], "application/json, text/event-stream")
            self.assertEqual(call["request"]["jsonrpc"], "2.0")
            self.assertIsInstance(call["request"]["id"], int)
            meta = call["request"]["params"]["_meta"]
            self.assertEqual(
                meta["io.modelcontextprotocol/protocolVersion"], MCP_PROTOCOL_VERSION
            )
            self.assertEqual(
                meta["io.modelcontextprotocol/clientInfo"],
                {"name": "tempera-voice", "version": "0.1.0"},
            )
            self.assertEqual(meta["io.modelcontextprotocol/clientCapabilities"], {})
        self.assertEqual(transport.calls[0]["request"]["method"], "server/discover")
        self.assertNotIn("initialize", [call["request"]["method"] for call in transport.calls])
        self.assertEqual(MCP_PROTOCOL_VERSION, "2026-07-28")
        self.assertEqual(transport.calls[1]["request"]["method"], "ping")
        self.assertEqual(transport.calls[2]["request"]["method"], "tools/list")

    def test_json_rpc_request_bodies_use_the_exact_compact_wire_shape(self):
        client, transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": {}}
        )
        client.ping()
        self.assertEqual(
            transport.calls[0]["data"],
            b'{"jsonrpc":"2.0","id":1,"method":"ping","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"tempera-sdk","version":"0.13.0"},"io.modelcontextprotocol/clientCapabilities":{}}}}',
        )

    def test_call_tool_whoami_and_status_wrap_tools_call(self):
        client, transport = gateway_client(
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"resultType": "complete", "content": [{"type": "text", "text": "{}"}], "isError": False},
            }
        )
        client.call_tool("tempera_search", {"query": "browser capability"})
        client.whoami()
        client.status()
        self.assertEqual(transport.calls[0]["request"]["method"], "tools/call")
        self.assertEqual(transport.calls[0]["request"]["params"]["name"], "tempera_search")
        self.assertEqual(
            transport.calls[0]["request"]["params"]["arguments"],
            {"query": "browser capability"},
        )
        self.assertEqual(
            transport.calls[0]["headers"][MCP_NAME_HEADER], "tempera_search"
        )
        self.assertEqual(transport.calls[1]["request"]["params"]["name"], "tempera_whoami")
        self.assertEqual(transport.calls[2]["request"]["params"]["name"], "tempera_status")

    def test_caller_meta_is_preserved_but_protocol_identity_is_authoritative(self):
        client, transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": {}}
        )
        client.rpc(
            "ping",
            {
                "_meta": {
                    "traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
                    "io.modelcontextprotocol/protocolVersion": "wrong",
                }
            },
        )
        meta = transport.calls[0]["request"]["params"]["_meta"]
        self.assertEqual(meta["traceparent"], "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01")
        self.assertEqual(meta["io.modelcontextprotocol/protocolVersion"], "2026-07-28")

    def test_sse_notifications_are_ignored_and_matching_response_is_returned(self):
        client, _transport = gateway_client(
            lambda request: (
                'event: message\ndata: {"jsonrpc":"2.0","method":"notifications/resources/updated"}\n\n'
                f'data: {{"jsonrpc":"2.0","id":{request["id"]},"result":{{"tools":[]}}}}\n\n'
            )
        )
        self.assertEqual(client.rpc("tools/list"), {"tools": []})

    def test_same_id_server_request_is_not_mistaken_for_the_response(self):
        client, _transport = gateway_client(
            lambda request: (
                f'data: {{"jsonrpc":"2.0","id":{request["id"]},"method":"sampling/createMessage","params":{{}}}}\n\n'
                f'data: {{"jsonrpc":"2.0","id":{request["id"]},"result":{{}}}}\n\n'
            )
        )
        self.assertEqual(client.ping(), {})

    def test_non_empty_client_capabilities_are_rejected_until_dispatch_exists(self):
        with self.assertRaisesRegex(TemperaSdkError, "must stay empty"):
            TemperaMcpClient(
                url="https://api.tempera.dev/mcp",
                bearer="tp_key_1",
                client_capabilities={"sampling": {}},
            )
        with self.assertRaisesRegex(TemperaSdkError, "client_name"):
            TemperaMcpClient(url="https://api.tempera.dev/mcp", bearer="tp_key_1", client_name="")
        client, _ = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": discovery_result()}
        )
        with self.assertRaisesRegex(TemperaSdkError, "client version"):
            client.discover(version="")

    def test_invalid_params_meta_and_missing_response_id_fail_closed(self):
        client, _transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"] + 1, "result": {}}
        )
        with self.assertRaisesRegex(TemperaSdkError, "params must be an object"):
            client.rpc("ping", [])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TemperaSdkError, "params._meta must be an object"):
            client.rpc("ping", {"_meta": []})
        with self.assertRaisesRegex(TemperaSdkError, "safe routing value"):
            client.call_tool("bad\r\nheader")
        with self.assertRaisesRegex(TemperaSdkError, "omitted request id"):
            client.ping()

    def test_invalid_json_rpc_envelopes_duplicate_ids_and_unsafe_bearers_fail_closed(self):
        handlers = [
            lambda request: {"jsonrpc": "2.0", "id": True, "result": {}},
            lambda request: {"jsonrpc": "1.0", "id": request["id"], "result": {}},
            lambda request: {"jsonrpc": "2.0", "id": request["id"]},
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {},
                "error": {},
            },
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {},
                "error": None,
            },
            lambda request: (
                f'data: {{"jsonrpc":"2.0","id":{request["id"]},"result":{{}}}}\n\n'
                f'data: {{"jsonrpc":"2.0","id":{request["id"]},"result":{{}}}}\n\n'
            ),
        ]
        for handler in handlers:
            with self.subTest(handler=handler):
                client, _ = gateway_client(handler)
                with self.assertRaises(TemperaSdkError):
                    client.ping()
        client, _ = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": {}}
        )
        with self.assertRaisesRegex(TemperaSdkError, "tool name"):
            client.rpc("tools/call", {})
        with self.assertRaisesRegex(TemperaSdkError, "arguments must be an object"):
            client.call_tool("tempera_status", [])  # type: ignore[arg-type]
        unsafe, _ = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": {}}
        )
        unsafe.bearer = "token\r\nheader"
        with self.assertRaisesRegex(TemperaSdkError, "unsafe header"):
            unsafe.ping()

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
            client.call_tool("tempera_search", {"query": "browser capability"})
        self.assertEqual(ctx.exception.code, -32002)
        self.assertEqual(ctx.exception.data, {"error": "plan_limit_exceeded"})

    def test_tool_error_and_input_required_outcomes_never_look_completed(self):
        outcomes = iter(
            [
                {
                    "resultType": "complete",
                    "isError": True,
                    "content": [{"type": "text", "text": "provider rejected the call"}],
                },
                {"resultType": "input_required"},
                {
                    "resultType": "input_required",
                    "requestState": "opaque-next-step",
                    "inputRequests": {
                        "approval": {
                            "method": "elicitation/create",
                            "params": {"message": "Approve?"},
                        },
                        "roots": {"method": "roots/list"},
                    },
                },
                {"resultType": "futureOutcome"},
                "not-an-object",
            ]
        )
        client, _ = gateway_client(
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": next(outcomes),
            }
        )
        with self.assertRaises(TemperaMcpError) as tool_error:
            client.call_tool("tempera_invoke")
        self.assertEqual(tool_error.exception.code, 0)
        self.assertTrue(tool_error.exception.data["isError"])
        with self.assertRaises(TemperaMcpError) as empty_input_required:
            client.call_tool("tempera_execute_plan")
        self.assertIn("malformed", str(empty_input_required.exception))
        with self.assertRaises(TemperaMcpInputRequired) as input_required:
            client.call_tool("tempera_execute_plan")
        self.assertEqual(input_required.exception.result["requestState"], "opaque-next-step")
        with self.assertRaises(TemperaMcpError) as unsupported:
            client.call_tool("tempera_execute_plan")
        self.assertEqual(unsupported.exception.data["resultType"], "futureOutcome")
        with self.assertRaises(TemperaMcpError) as malformed:
            client.call_tool("tempera_execute_plan")
        self.assertEqual(malformed.exception.data, "not-an-object")

    def test_discovery_catalog_complete_results_and_continuation_fail_closed(self):
        outcomes = iter(
            [
                {},
                {**discovery_result(), "supportedVersions": ["2025-06-18"]},
                {"resultType": "complete", "tools": {}},
                {"resultType": "complete"},
                {"resultType": "complete", "content": [1]},
                {"resultType": "complete", "content": [{"type": "text", "text": "x", "_meta": []}]},
                {"resultType": "complete", "content": []},
            ]
        )
        client, transport = gateway_client(
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": next(outcomes),
            }
        )
        with self.assertRaises(TemperaMcpError):
            client.discover()
        with self.assertRaises(TemperaMcpError):
            client.discover()
        with self.assertRaises(TemperaMcpError):
            client.list_tools()
        with self.assertRaisesRegex(TemperaMcpError, "empty complete"):
            client.call_tool("tempera_execute_plan")
        with self.assertRaisesRegex(TemperaMcpError, "malformed complete"):
            client.call_tool("tempera_execute_plan")
        with self.assertRaisesRegex(TemperaMcpError, "malformed complete"):
            client.call_tool("tempera_execute_plan")
        result = client.call_tool(
            "tempera_execute_plan",
            input_responses={"approval": {"accepted": True}},
            request_state="opaque-next-step",
        )
        self.assertEqual(result["resultType"], "complete")
        params = transport.calls[-1]["request"]["params"]
        self.assertEqual(params["inputResponses"], {"approval": {"accepted": True}})
        self.assertEqual(params["requestState"], "opaque-next-step")

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
    def test_string_error_fails_closed_as_a_malformed_envelope(self):
        client, _calls = gateway_client(lambda request: {"jsonrpc": "2.0", "id": 1, "error": "nope"})
        with self.assertRaises(TemperaSdkError) as caught:
            client.ping()
        self.assertIn("malformed error object", str(caught.exception))

    def test_empty_error_object_is_not_silently_treated_as_success(self):
        client, _calls = gateway_client(lambda request: {"jsonrpc": "2.0", "id": 1, "error": {}})
        with self.assertRaises(TemperaSdkError) as caught:
            client.ping()
        self.assertIn("malformed error object", str(caught.exception))
