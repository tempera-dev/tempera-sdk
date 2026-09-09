from concurrent.futures import ThreadPoolExecutor
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
from tempera_sdk.mcp import (
    _CATALOG_JSON_ENCODER,
    _MAX_REQUEST_ID,
    _MAX_TOOL_CATALOG_BYTES,
    _MAX_TOOL_PAGE_BYTES,
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
                return {"jsonrpc": "2.0", "id": request["id"], "result": {"tools": [{"name": "tempera_whoami", "inputSchema": {}}]}}
            return {"jsonrpc": "2.0", "id": request["id"], "result": {}}

        client, transport = gateway_client(handler)
        client.initialize()
        client.ping()
        tools = client.list_tools()
        self.assertEqual(tools, [{"name": "tempera_whoami", "inputSchema": {}}])
        for call in transport.calls:
            self.assertEqual(call["headers"]["authorization"], "Bearer tp_key_1")
            self.assertEqual(call["request"]["jsonrpc"], "2.0")
            self.assertIsInstance(call["request"]["id"], int)
        self.assertEqual(transport.calls[0]["request"]["method"], "server/discover")
        self.assertEqual(transport.calls[0]["request"]["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"], "2026-07-28")
        self.assertEqual(transport.calls[0]["request"]["params"]["_meta"]["io.modelcontextprotocol/clientInfo"], {"name": "tempera-sdk", "version": "0.12.0"})
        self.assertEqual(MCP_PROTOCOL_VERSION, "2026-07-28")
        for call in transport.calls:
            self.assertEqual(call["headers"]["mcp-protocol-version"], "2026-07-28")
            self.assertEqual(call["headers"]["mcp-method"], call["request"]["method"])
        self.assertEqual(transport.calls[1]["request"]["method"], "ping")
        self.assertEqual(transport.calls[2]["request"]["method"], "tools/list")

    def test_json_rpc_request_bodies_use_the_compact_wire_shape(self):
        client, transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": {}}
        )
        client.ping()
        self.assertEqual(
            transport.calls[0]["data"],
            b'{"jsonrpc":"2.0","id":1,"method":"ping","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}',
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
            {
                "name": "cradle_get_capabilities",
                "arguments": {"verbose": True},
                "_meta": {
                    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                    "io.modelcontextprotocol/clientCapabilities": {},
                },
            },
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


class NonConformantErrorTest(unittest.TestCase):
    def test_string_error_is_a_protocol_failure(self):
        client, _calls = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "error": "nope"}
        )
        with self.assertRaises(TemperaSdkError) as caught:
            client.ping()
        self.assertIn("malformed error", str(caught.exception))


def complete_tool(name="tempera_whoami", **extra):
    return {"name": name, "inputSchema": {}, **extra}


def normalized_size(value):
    return sum(len(fragment.encode("utf-8")) for fragment in _CATALOG_JSON_ENCODER.iterencode(value))


def catalog_page_of_size(size, *, next_cursor=None):
    """Build a page whose normalized JSON is exactly ``size`` bytes."""
    page = {"tools": [], "padding": ""}
    if next_cursor is not None:
        page["nextCursor"] = next_cursor
    page["padding"] = "x" * (size - normalized_size(page))
    assert normalized_size(page) == size
    return page


class StrictJsonRpcResponseTest(unittest.TestCase):
    def test_null_result_is_a_valid_json_rpc_result(self):
        client, transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": None}
        )
        self.assertIsNone(client.ping())
        self.assertEqual(len(transport.calls), 1)

    def test_rejects_poisoned_response_envelopes_without_retrying(self):
        poisoned = (
            {"id": 1, "result": {}},
            {"jsonrpc": "1.0", "id": 1, "result": {}},
            {"jsonrpc": "2.0", "id": "1", "result": {}},
            {"jsonrpc": "2.0", "id": True, "result": {}},
            {"jsonrpc": "2.0", "id": None, "result": {}},
            {"jsonrpc": "2.0", "id": 1.0, "result": {}},
            {"jsonrpc": "2.0", "id": 9_007_199_254_740_992, "result": {}},
            {"jsonrpc": "2.0", "id": 1, "result": {}, "error": {"code": -1, "message": "bad"}},
            {"jsonrpc": "2.0", "id": 1},
        )
        for response in poisoned:
            with self.subTest(response=response):
                client, transport = gateway_client(lambda request, response=response: response)
                with self.assertRaises(TemperaSdkError):
                    client.ping()
                self.assertEqual(len(transport.calls), 1)

    def test_rejects_malformed_error_without_retrying(self):
        malformed_errors = (
            "legacy error",
            {"code": True, "message": "no boolean code"},
            {"code": "-32000", "message": "no string code"},
            {"code": -32000, "message": None},
        )
        for error in malformed_errors:
            with self.subTest(error=error):
                client, transport = gateway_client(
                    lambda request, error=error: {"jsonrpc": "2.0", "id": request["id"], "error": error}
                )
                with self.assertRaises(TemperaSdkError):
                    client.ping()
                self.assertEqual(len(transport.calls), 1)


class RequestIdTest(unittest.TestCase):
    def test_concurrent_requests_receive_unique_exact_ids(self):
        client, transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": request["id"]}
        )
        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(lambda _: client.ping(), range(128)))
        self.assertEqual(sorted(results), list(range(1, 129)))
        self.assertEqual(sorted(call["request"]["id"] for call in transport.calls), list(range(1, 129)))

    def test_request_id_exhaustion_sends_no_extra_post(self):
        client, transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": {}}
        )
        client._next_id = _MAX_REQUEST_ID
        client.ping()
        with self.assertRaises(TemperaSdkError):
            client.ping()
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(transport.calls[0]["request"]["id"], _MAX_REQUEST_ID)


class ToolPaginationTest(unittest.TestCase):
    def test_two_page_opaque_cursor_preserves_headers_and_metadata(self):
        def handler(request):
            if len(transport.calls) == 1:
                return {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {"tools": [complete_tool("first")], "nextCursor": "opaque/A"},
                }
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"tools": [complete_tool("second")]},
            }

        client, transport = gateway_client(handler)
        self.assertEqual([tool["name"] for tool in client.list_tools()], ["first", "second"])
        self.assertEqual(len(transport.calls), 2)
        self.assertNotIn("cursor", transport.calls[0]["request"]["params"])
        self.assertEqual(transport.calls[1]["request"]["params"]["cursor"], "opaque/A")
        for call in transport.calls:
            self.assertEqual(call["headers"]["mcp-protocol-version"], MCP_PROTOCOL_VERSION)
            self.assertEqual(call["headers"]["mcp-method"], "tools/list")
            self.assertEqual(
                call["request"]["params"]["_meta"]["io.modelcontextprotocol/clientCapabilities"],
                {},
            )

    def test_rejects_nonadjacent_cursor_cycle_without_a_third_retry(self):
        pages = (
            {"tools": [complete_tool("first")], "nextCursor": "A"},
            {"tools": [complete_tool("second")], "nextCursor": "B"},
            {"tools": [complete_tool("third")], "nextCursor": "A"},
        )
        client, transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": pages[len(transport.calls) - 1]}
        )
        with self.assertRaises(TemperaSdkError):
            client.list_tools()
        self.assertEqual(len(transport.calls), 3)

    def test_rejects_empty_null_and_non_string_next_cursor(self):
        for cursor in ("", None, 7):
            with self.subTest(cursor=cursor):
                client, transport = gateway_client(
                    lambda request, cursor=cursor: {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": {"tools": [], "nextCursor": cursor},
                    }
                )
                with self.assertRaises(TemperaSdkError):
                    client.list_tools()
                self.assertEqual(len(transport.calls), 1)

    def test_allows_one_hundred_pages_and_rejects_the_next_page(self):
        def one_hundred_pages(request):
            page_number = len(one_hundred_calls.calls)
            result = {"tools": []}
            if page_number < 100:
                result["nextCursor"] = f"cursor-{page_number}"
            return {"jsonrpc": "2.0", "id": request["id"], "result": result}

        one_hundred_client, one_hundred_calls = gateway_client(one_hundred_pages)
        self.assertEqual(one_hundred_client.list_tools(), [])
        self.assertEqual(len(one_hundred_calls.calls), 100)

        def one_hundred_one_pages(request):
            page_number = len(one_hundred_one_calls.calls)
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"tools": [], "nextCursor": f"cursor-{page_number}"},
            }

        one_hundred_one_client, one_hundred_one_calls = gateway_client(one_hundred_one_pages)
        with self.assertRaises(TemperaSdkError):
            one_hundred_one_client.list_tools()
        self.assertEqual(len(one_hundred_one_calls.calls), 100)

    def test_allows_ten_thousand_items_and_rejects_one_more_before_validation(self):
        accepted = [complete_tool(f"tool_{index}") for index in range(10_000)]
        client, transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": {"tools": accepted}}
        )
        self.assertEqual(len(client.list_tools()), 10_000)
        self.assertEqual(len(transport.calls), 1)

        rejected = [object()] * 10_001
        client, transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": {"tools": rejected}}
        )
        with self.assertRaises(TemperaSdkError) as caught:
            client.list_tools()
        self.assertIn("item limit", str(caught.exception))
        self.assertEqual(len(transport.calls), 1)


class ToolCatalogValidationTest(unittest.TestCase):
    def test_rejects_poisoned_descriptors(self):
        poisoned_pages = (
            {"tools": [None]},
            {"tools": [{"inputSchema": {}}]},
            {"tools": [complete_tool("")]},
            {"tools": [complete_tool("bad\x00name")]},
            {"tools": [{"name": "missing_schema"}]},
            {"tools": [complete_tool("schema_list", inputSchema=[])]},
            {"tools": [complete_tool("null_description", description=None)]},
            {"tools": [complete_tool("duplicate"), complete_tool("duplicate")]},
        )
        for page in poisoned_pages:
            with self.subTest(page=page):
                client, transport = gateway_client(
                    lambda request, page=page: {"jsonrpc": "2.0", "id": request["id"], "result": page}
                )
                with self.assertRaises(TemperaSdkError):
                    client.list_tools()
                self.assertEqual(len(transport.calls), 1)

    def test_rejects_cycles_nonfinite_non_json_and_excessive_nesting(self):
        first = {}
        second = {"back": first}
        first["forward"] = second
        deeply_nested = {}
        current = deeply_nested
        for _ in range(101):
            current["next"] = {}
            current = current["next"]
        poisoned_metadata = (
            first,
            float("nan"),
            object(),
            deeply_nested,
        )
        for metadata in poisoned_metadata:
            with self.subTest(metadata_type=type(metadata).__name__):
                client, transport = gateway_client(
                    lambda request, metadata=metadata: {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": {"tools": [], "unknownMetadata": metadata},
                    }
                )
                with self.assertRaises(TemperaSdkError):
                    client.list_tools()
                self.assertEqual(len(transport.calls), 1)

    def test_byte_guard_stops_before_traversing_a_wide_metadata_value(self):
        from unittest.mock import patch

        visits = []

        class ObservedList(list):
            def __iter__(self):
                for value in super().__iter__():
                    visits.append(value)
                    if len(visits) > 100:
                        raise AssertionError("oversized metadata was fully traversed")
                    yield value

        client, transport = gateway_client(
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"tools": [], "metadata": ObservedList([0] * 200)},
            }
        )
        with patch("tempera_sdk.mcp._MAX_TOOL_PAGE_BYTES", 64):
            with self.assertRaises(TemperaSdkError):
                client.list_tools()
        self.assertGreater(len(visits), 0)
        self.assertLess(len(visits), 100)
        self.assertEqual(len(transport.calls), 1)

    def test_normalized_page_and_total_byte_limits_are_exact(self):
        exact_page = catalog_page_of_size(_MAX_TOOL_PAGE_BYTES)
        client, transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": exact_page}
        )
        self.assertEqual(client.list_tools(), [])
        self.assertEqual(len(transport.calls), 1)

        too_large_page = catalog_page_of_size(_MAX_TOOL_PAGE_BYTES + 1)
        client, transport = gateway_client(
            lambda request: {"jsonrpc": "2.0", "id": request["id"], "result": too_large_page}
        )
        with self.assertRaises(TemperaSdkError):
            client.list_tools()
        self.assertEqual(len(transport.calls), 1)

        page_size = 950_000
        final_size = _MAX_TOOL_CATALOG_BYTES - (8 * page_size)
        exact_total_pages = [
            catalog_page_of_size(page_size, next_cursor=f"cursor-{index}") for index in range(8)
        ] + [catalog_page_of_size(final_size)]
        client, transport = gateway_client(
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": exact_total_pages[len(transport.calls) - 1],
            }
        )
        self.assertEqual(client.list_tools(), [])
        self.assertEqual(len(transport.calls), 9)

        too_large_total_pages = exact_total_pages[:-1] + [catalog_page_of_size(final_size + 1)]
        client, transport = gateway_client(
            lambda request: {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": too_large_total_pages[len(transport.calls) - 1],
            }
        )
        with self.assertRaises(TemperaSdkError):
            client.list_tools()
        self.assertEqual(len(transport.calls), 9)


if __name__ == "__main__":
    unittest.main()
