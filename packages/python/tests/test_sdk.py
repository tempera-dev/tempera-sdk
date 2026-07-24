import unittest

from tempera_sdk import (
    API_TARGETS,
    AUDIENCES,
    DEFAULT_AUDIENCE,
    ENVIRONMENTS,
    OPERATIONS,
    PRODUCTS,
    SCOPES,
)


class TemperaSdkTest(unittest.TestCase):
    def test_product_registry_covers_every_product_with_palette_included(self):
        self.assertEqual(PRODUCTS["controlPlane"]["repository"], "https://github.com/tempera-dev/auth-hub")
        self.assertEqual(PRODUCTS["palette"]["repository"], "https://github.com/tempera-dev/palette")
        self.assertEqual(PRODUCTS["tempo"]["repository"], "https://github.com/tempera-dev/tempo")
        self.assertEqual(PRODUCTS["temperaLlm"]["repository"], "https://github.com/tempera-dev/tempera-llm")
        self.assertEqual(PRODUCTS["temperaWorkflows"]["repository"], "https://github.com/tempera-dev/tempera-workflows")
        self.assertEqual(PRODUCTS["temperaGym"]["repository"], "https://github.com/tempera-dev/tempera-gym")
        self.assertEqual(PRODUCTS["cradle"]["repository"], "https://github.com/tempera-dev/cradle")
        self.assertEqual(PRODUCTS["remi"]["repository"], "https://github.com/tempera-dev/remi")
        self.assertEqual(PRODUCTS["dataEngine"]["repository"], "https://github.com/tempera-dev/data-engine")
        self.assertEqual(PRODUCTS["humanData"]["repository"], "https://github.com/tempera-dev/human-data")
        self.assertEqual(PRODUCTS["tempJs"]["repository"], "https://github.com/tempera-dev/temp.js")
        self.assertEqual(PRODUCTS["tempOS"]["repository"], "https://github.com/tempera-dev/tempOS")
        self.assertEqual(PRODUCTS["arrha"]["repository"], "https://github.com/tempera-dev/arrha")

    def test_audience_bearing_products_map_to_registered_audiences(self):
        for key, product in PRODUCTS.items():
            if product["audience"] is not None:
                self.assertIn(product["audience"], AUDIENCES, f"{key} audience registered")
        self.assertIn(DEFAULT_AUDIENCE, AUDIENCES)
        self.assertIn("tempera-mcp", AUDIENCES)
        self.assertIn("human-data", AUDIENCES)
        self.assertIn("data-engine", AUDIENCES)
        self.assertIn("tempera-code", AUDIENCES)
        self.assertIn("tempera-llm", AUDIENCES)
        self.assertIn("tempera-workflows", AUDIENCES)
        self.assertIn("tempera-gym", AUDIENCES)

    def test_scopes_match_the_control_plane_scope_registry(self):
        self.assertEqual(
            list(SCOPES),
            [
                "mcp:invoke", "memory:read", "memory:write", "memory:manage",
                "trace:read", "trace:write", "dataset:read", "dataset:write",
                "eval:run", "training:publish", "review:gold:manage",
                "review:resolve", "workflow:read", "workflow:write",
                "workflow:run", "bio:source:read", "bio:proposal:write",
                "bio:measurement:verify", "bio:decision:write",
                "bio:experiment:approve", "bio:experiment:submit",
                "bio:signer:manage", "model:read", "model:invoke",
                "usage:reserve", "pii:unmask", "admin",
            ],
        )

    def test_all_four_environments_carry_the_same_target_keys(self):
        environment_names = list(ENVIRONMENTS)
        self.assertEqual(environment_names, ["local", "preview", "staging", "production"])
        keys = sorted(ENVIRONMENTS["local"])
        for name in environment_names:
            self.assertEqual(sorted(ENVIRONMENTS[name]), keys, name)
        self.assertEqual(ENVIRONMENTS["production"]["controlPlaneUrl"], "https://api.tempera.dev")
        self.assertEqual(ENVIRONMENTS["production"]["mcpGatewayUrl"], "https://api.tempera.dev/mcp")
        self.assertEqual(ENVIRONMENTS["production"]["paletteMcpUrl"], "https://mcp.tempera.dev/mcp")
        self.assertEqual(ENVIRONMENTS["production"]["tempoApiUrl"], "https://tempo.tempera.dev")
        self.assertEqual(ENVIRONMENTS["production"]["temperaLlmApiUrl"], "https://llm.tempera.dev")
        self.assertEqual(ENVIRONMENTS["production"]["temperaWorkflowsApiUrl"], "https://workflows.tempera.dev")
        self.assertEqual(ENVIRONMENTS["production"]["temperaGymUrl"], "https://gym.tempera.dev")
        # Deprecated alias points at the same object.
        self.assertIs(API_TARGETS, ENVIRONMENTS)

    def test_every_operation_has_a_unique_snake_case_id_and_sentence_description(self):
        for product_key, ops in OPERATIONS.items():
            seen = set()
            for op in ops:
                label = f"{product_key}.{op['id']}"
                self.assertNotIn(op["id"], seen, f"{label} unique")
                seen.add(op["id"])
                self.assertRegex(op["id"], r"^[a-z][a-z0-9_]*$", f"{label} snake_case")
                self.assertTrue(op["upstream_operation_id"], f"{label} producer operation id")
                self.assertRegex(op["description"], r"^[A-Z].*\.$", f"{label} description sentence")
                self.assertIn(op["method"], ("GET", "POST", "PUT", "PATCH", "DELETE"))


if __name__ == "__main__":
    unittest.main()
