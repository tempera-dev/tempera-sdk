import asyncio
import dataclasses
import unittest
from typing import Literal

from tempera_sdk import (
    MCP_PROVIDER_PROTOCOL_VERSION,
    ProviderArgumentError,
    ProviderDefinitionError,
    TemperaProvider,
)


@dataclasses.dataclass
class Point:
    x: int
    y: int = 2


class ProviderAuthoringTest(unittest.TestCase):
    def test_decorator_compiles_closed_schema_once_and_calls_by_keyword(self):
        app = TemperaProvider("math")

        @app.tool(read_only=True, idempotent=True)
        def add(a: int, b: int = 1) -> int:
            """Add two integers."""
            return a + b

        tools = app.handle({"method": "tools/list"})["tools"]
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "add")
        self.assertEqual(tools[0]["description"], "Add two integers.")
        self.assertEqual(tools[0]["inputSchema"], {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer", "default": 1}}, "additionalProperties": False, "required": ["a"]})
        self.assertTrue(tools[0]["annotations"]["readOnlyHint"])
        self.assertTrue(tools[0]["annotations"]["idempotentHint"])
        result = app.handle({"method": "tools/call", "params": {"name": "add", "arguments": {"a": 41}}})
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"], {"value": 42})

    def test_discovery_is_tool_only_private_and_protocol_current(self):
        app = TemperaProvider("demo", version="2.0.0")
        discovery = app.handle({"method": "server/discover"})
        self.assertEqual(MCP_PROVIDER_PROTOCOL_VERSION, "2026-07-28")
        self.assertEqual(discovery["supportedVersions"], ["2026-07-28"])
        self.assertEqual(discovery["capabilities"], {"tools": {}})
        self.assertEqual(discovery["cacheScope"], "private")
        self.assertEqual(discovery["ttlMs"], 0)
        self.assertEqual(discovery["serverInfo"], {"name": "demo", "version": "2.0.0"})

    def test_tool_order_is_deterministic_independent_of_registration_order(self):
        app = TemperaProvider("ordered")

        @app.tool
        def zeta(value: str) -> str:
            return value

        @app.tool
        def alpha(value: str) -> str:
            return value

        names = [tool["name"] for tool in app.handle({"method": "tools/list"})["tools"]]
        self.assertEqual(names, ["alpha", "zeta"])

    def test_invalid_arguments_fail_before_user_code_runs(self):
        app = TemperaProvider("safe")
        calls = []

        @app.tool
        def add(a: int, b: int) -> int:
            calls.append((a, b))
            return a + b

        with self.assertRaisesRegex(ProviderArgumentError, "a must be int"):
            app.handle({"method": "tools/call", "params": {"name": "add", "arguments": {"a": True, "b": 2}}})
        with self.assertRaisesRegex(ProviderArgumentError, "unknown arguments"):
            app.handle({"method": "tools/call", "params": {"name": "add", "arguments": {"a": 1, "b": 2, "c": 3}}})
        self.assertEqual(calls, [])

    def test_dataclass_literal_optional_and_collection_contracts(self):
        app = TemperaProvider("typed")

        @app.tool(read_only=True)
        def inspect_point(point: Point, mode: Literal["brief", "full"] = "brief", tags: list[str] | None = None) -> dict[str, object]:
            return {"sum": point.x + point.y, "mode": mode, "tags": tags or []}

        schema = app.handle({"method": "tools/list"})["tools"][0]["inputSchema"]
        self.assertEqual(schema["properties"]["point"]["type"], "object")
        self.assertEqual(schema["properties"]["point"]["required"], ["x"])
        self.assertEqual(schema["properties"]["mode"]["enum"], ["brief", "full"])
        self.assertIn("anyOf", schema["properties"]["tags"])
        result = app.handle({"method": "tools/call", "params": {"name": "inspect_point", "arguments": {"point": {"x": 40}, "mode": "full", "tags": ["a"]}}})
        self.assertEqual(result["structuredContent"], {"sum": 42, "mode": "full", "tags": ["a"]})

    def test_duplicate_and_contradictory_definitions_fail_at_registration(self):
        app = TemperaProvider("definitions")

        @app.tool(name="same")
        def first(value: str) -> str:
            return value

        with self.assertRaisesRegex(ProviderDefinitionError, "duplicate tool name"):
            @app.tool(name="same")
            def second(value: str) -> str:
                return value

        with self.assertRaisesRegex(ProviderDefinitionError, "read-only tool cannot be destructive"):
            @app.tool(read_only=True, destructive=True)
            def contradictory() -> None:
                return None

    def test_application_exceptions_are_redacted_from_protocol_results(self):
        app = TemperaProvider("redaction")

        @app.tool
        def explode() -> None:
            raise RuntimeError("super-secret-internal-detail")

        result = app.handle({"method": "tools/call", "params": {"name": "explode", "arguments": {}}})
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"], {"error": "tool_execution_failed"})
        self.assertNotIn("super-secret", str(result))

    def test_async_function_is_rejected_by_sync_path_before_invocation(self):
        app = TemperaProvider("async-sync-boundary")
        calls = []

        @app.tool
        async def async_tool(value: int) -> int:
            calls.append(value)
            return value

        with self.assertRaisesRegex(ProviderDefinitionError, "async tool requires handle_async"):
            app.handle({"method": "tools/call", "params": {"name": "async_tool", "arguments": {"value": 1}}})
        self.assertEqual(calls, [])


class AsyncProviderAuthoringTest(unittest.IsolatedAsyncioTestCase):
    async def test_handle_async_awaits_async_tools_and_accepts_sync_tools(self):
        app = TemperaProvider("async")

        @app.tool(read_only=True)
        async def async_add(a: int, b: int) -> int:
            await asyncio.sleep(0)
            return a + b

        @app.tool(read_only=True)
        def sync_add(a: int, b: int) -> int:
            return a + b

        async_result = await app.handle_async({"method": "tools/call", "params": {"name": "async_add", "arguments": {"a": 20, "b": 22}}})
        sync_result = await app.handle_async({"method": "tools/call", "params": {"name": "sync_add", "arguments": {"a": 19, "b": 23}}})
        self.assertEqual(async_result["structuredContent"], {"value": 42})
        self.assertEqual(sync_result["structuredContent"], {"value": 42})

    async def test_async_application_exception_is_redacted(self):
        app = TemperaProvider("async-redaction")

        @app.tool
        async def explode() -> None:
            await asyncio.sleep(0)
            raise RuntimeError("async-super-secret")

        result = await app.handle_async({"method": "tools/call", "params": {"name": "explode", "arguments": {}}})
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"], {"error": "tool_execution_failed"})
        self.assertNotIn("async-super-secret", str(result))

    async def test_async_argument_validation_happens_before_user_code(self):
        app = TemperaProvider("async-validation")
        calls = []

        @app.tool
        async def typed(value: int) -> int:
            calls.append(value)
            return value

        with self.assertRaisesRegex(ProviderArgumentError, "value must be int"):
            await app.handle_async({"method": "tools/call", "params": {"name": "typed", "arguments": {"value": True}}})
        self.assertEqual(calls, [])

    async def test_async_discovery_and_listing_match_sync_contract(self):
        app = TemperaProvider("async-discovery")

        @app.tool
        async def zeta(value: int) -> int:
            return value

        @app.tool
        def alpha(value: int) -> int:
            return value

        discovery = await app.handle_async({"method": "server/discover"})
        listing = await app.handle_async({"method": "tools/list"})
        self.assertEqual(discovery, app.handle({"method": "server/discover"}))
        self.assertEqual([tool["name"] for tool in listing["tools"]], ["alpha", "zeta"])


if __name__ == "__main__":
    unittest.main()
