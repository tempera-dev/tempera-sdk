import json
import unittest

from tempera_sdk import TemperaAuth, TemperaClient


class LlmToolWireTest(unittest.TestCase):
    def test_tool_turns_nulls_omissions_and_final_json(self):
        tool_message = {"role": "assistant", "content": None, "tool_calls": [
            {"id": "call_1", "type": "function", "function": {"name": "inspect", "arguments": "{}"}}
        ]}
        base = {"model": "gpt-4o-mini", "max_tokens": 64, "messages": [
            {"role": "user", "content": "inspect"}, tool_message,
            {"role": "tool", "tool_call_id": "call_1", "content": "{}"}
        ]}
        cases = [base, dict(base, tools=None, tool_choice=None), dict(base,
            tools=[{"type": "function", "function": {"name": "inspect", "parameters": {"type": "object"}}}],
            tool_choice={"type": "function", "function": {"name": "inspect"}},
            parallel_tool_calls=False), dict(base, tool_choice="none", response_format={
                "type": "json_schema", "json_schema": {"name": "final", "schema": {"type": "object"}}
            })]
        result = {"choices": [{"message": tool_message, "finish_reason": "tool_calls"}]}

        def transport(method, url, headers, data):
            self.assertEqual(method, "POST")
            self.assertEqual(url, "http://127.0.0.1:8080/v1/chat/completions")
            self.assertEqual(headers["authorization"], "Bearer fixture-key")
            self.assertEqual(json.loads(data), expected)
            return result

        client = TemperaClient(
            auth=TemperaAuth(issuer_url="https://issuer.example.test", api_key="fixture-key"),
            base_urls={"tempera_llm": "http://127.0.0.1:8080"}, transport=transport,
        )
        for expected in cases:
            with self.subTest(keys=list(expected)):
                self.assertEqual(client.tempera_llm.create_chat_completion(expected), result)
