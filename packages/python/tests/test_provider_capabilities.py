import asyncio
import unittest

from tempera_sdk import ProviderArgumentError, ProviderDefinitionError, TemperaProvider


class ProviderCapabilitiesTest(unittest.TestCase):
    def test_discovery_lists_tools_resources_and_prompts_deterministically(self):
        app = TemperaProvider("full")

        @app.tool
        def echo(value: str) -> str:
            return value

        @app.resource("memory://zeta", name="zeta")
        def zeta_resource() -> str:
            return "zeta"

        @app.resource("memory://alpha", name="alpha")
        def alpha_resource() -> str:
            return "alpha"

        @app.prompt
        def zeta_prompt(topic: str) -> str:
            return topic

        @app.prompt
        def alpha_prompt(topic: str = "x") -> str:
            return topic

        discovery = app.handle({"method": "server/discover"})
        self.assertEqual(discovery["resultType"], "complete")
        self.assertEqual(discovery["capabilities"], {"tools": {}, "resources": {}, "prompts": {}})
        resources = app.handle({"method": "resources/list"})["resources"]
        prompts = app.handle({"method": "prompts/list"})["prompts"]
        self.assertEqual([item["uri"] for item in resources], ["memory://alpha", "memory://zeta"])
        self.assertEqual([item["name"] for item in prompts], ["alpha_prompt", "zeta_prompt"])

    def test_resource_text_and_binary_results_use_closed_wire_shapes(self):
        app = TemperaProvider("resources")

        @app.resource("memory://text", mime_type="text/plain")
        def text_resource() -> str:
            return "hello"

        @app.resource("memory://blob", mime_type="application/octet-stream")
        def blob_resource() -> bytes:
            return b"abc"

        text = app.handle({"method": "resources/read", "params": {"uri": "memory://text"}})
        blob = app.handle({"method": "resources/read", "params": {"uri": "memory://blob"}})
        self.assertEqual(text, {"resultType": "complete", "contents": [{"uri": "memory://text", "mimeType": "text/plain", "text": "hello"}]})
        self.assertEqual(blob, {"resultType": "complete", "contents": [{"uri": "memory://blob", "mimeType": "application/octet-stream", "blob": "YWJj"}]})

    def test_prompt_arguments_are_typed_and_validated_before_user_code(self):
        app = TemperaProvider("prompts")
        calls = []

        @app.prompt(description="Summarize a topic")
        def summarize(topic: str, count: int = 1) -> str:
            calls.append((topic, count))
            return f"{topic}:{count}"

        spec = app.handle({"method": "prompts/list"})["prompts"][0]
        by_name = {item["name"]: item for item in spec["arguments"]}
        self.assertTrue(by_name["topic"]["required"])
        self.assertFalse(by_name["count"]["required"])
        self.assertEqual(by_name["count"]["schema"], {"type": "integer", "default": 1})
        result = app.handle({"method": "prompts/get", "params": {"name": "summarize", "arguments": {"topic": "mcp", "count": 2}}})
        self.assertEqual(result, {"resultType": "complete", "messages": [{"role": "user", "content": {"type": "text", "text": "mcp:2"}}]})
        self.assertEqual(calls, [("mcp", 2)])
        with self.assertRaisesRegex(ProviderArgumentError, "count must be int"):
            app.handle({"method": "prompts/get", "params": {"name": "summarize", "arguments": {"topic": "mcp", "count": True}}})
        self.assertEqual(calls, [("mcp", 2)])

    def test_prompt_can_return_explicit_text_messages(self):
        app = TemperaProvider("messages")

        @app.prompt
        def debate(topic: str):
            return [
                {"role": "user", "content": {"type": "text", "text": topic}},
                {"role": "assistant", "content": {"type": "text", "text": "ready"}},
            ]

        result = app.handle({"method": "prompts/get", "params": {"name": "debate", "arguments": {"topic": "agents"}}})
        self.assertEqual([message["role"] for message in result["messages"]], ["user", "assistant"])

    def test_definition_collisions_and_resource_templates_fail_closed(self):
        app = TemperaProvider("definitions")

        @app.resource("memory://one", name="same")
        def one() -> str:
            return "one"

        with self.assertRaisesRegex(ProviderDefinitionError, "duplicate resource name"):
            @app.resource("memory://two", name="same")
            def two() -> str:
                return "two"

        with self.assertRaisesRegex(ProviderDefinitionError, "must not take arguments"):
            @app.resource("memory://template")
            def parameterized(value: str) -> str:
                return value

        with self.assertRaisesRegex(ProviderDefinitionError, "absolute URI"):
            app.resource("relative")

    def test_sync_path_rejects_async_resource_and_prompt_before_invocation(self):
        app = TemperaProvider("sync-boundary")
        calls = []

        @app.resource("memory://async")
        async def resource() -> str:
            calls.append("resource")
            return "value"

        @app.prompt
        async def prompt(value: str) -> str:
            calls.append("prompt")
            return value

        with self.assertRaisesRegex(ProviderDefinitionError, "async resource requires"):
            app.handle({"method": "resources/read", "params": {"uri": "memory://async"}})
        with self.assertRaisesRegex(ProviderDefinitionError, "async prompt requires"):
            app.handle({"method": "prompts/get", "params": {"name": "prompt", "arguments": {"value": "x"}}})
        self.assertEqual(calls, [])

    def test_application_failures_are_redacted_to_empty_optional_results(self):
        app = TemperaProvider("redaction")

        @app.resource("memory://secret")
        def bad_resource() -> str:
            raise RuntimeError("resource-secret")

        @app.prompt
        def bad_prompt() -> str:
            raise RuntimeError("prompt-secret")

        with self.assertRaisesRegex(RuntimeError, "resource execution failed") as resource:
            app.handle({"method": "resources/read", "params": {"uri": "memory://secret"}})
        with self.assertRaisesRegex(RuntimeError, "prompt execution failed") as prompt:
            app.handle({"method": "prompts/get", "params": {"name": "bad_prompt", "arguments": {}}})
        self.assertNotIn("secret", str(resource.exception) + str(prompt.exception))


class AsyncProviderCapabilitiesTest(unittest.IsolatedAsyncioTestCase):
    async def test_async_resources_and_prompts_are_awaited(self):
        app = TemperaProvider("async")

        @app.resource("memory://async")
        async def resource() -> str:
            await asyncio.sleep(0)
            return "async-value"

        @app.prompt
        async def prompt(value: str) -> str:
            await asyncio.sleep(0)
            return value.upper()

        resource_result = await app.handle_async({"method": "resources/read", "params": {"uri": "memory://async"}})
        prompt_result = await app.handle_async({"method": "prompts/get", "params": {"name": "prompt", "arguments": {"value": "hello"}}})
        self.assertEqual(resource_result["contents"][0]["text"], "async-value")
        self.assertEqual(prompt_result["messages"][0]["content"]["text"], "HELLO")


if __name__ == "__main__":
    unittest.main()
