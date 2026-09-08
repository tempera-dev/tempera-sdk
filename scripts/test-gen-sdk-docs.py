#!/usr/bin/env python3
"""Generated credential guidance follows the exact vendored Auth contract."""
import importlib.util
import json
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("gen_sdk_docs", Path(__file__).with_name("gen-sdk-docs.py"))
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
SURFACE = json.loads(generator.SURFACE.read_text())


class AuthGuidanceTest(unittest.TestCase):
    def test_every_registered_non_key_scope_refuses_key_guidance(self):
        schemas = json.loads((generator.ROOT / "specs/control-plane.openapi.json").read_text())["components"]["schemas"]
        excluded = set(schemas["Scope"]["enum"]) - set(schemas["ApiKeyScope"]["enum"])
        for key, operations in SURFACE["operations"].items():
            for operation in operations:
                if operation["auth"] in ("oauthResource", "product") and operation.get("scope") in excluded:
                    with self.subTest(product=key, operation=operation["id"]):
                        label = generator.auth_label(SURFACE, key, operation)
                        self.assertIn("OAuth", label)
                        self.assertIn("cannot", label)
                        self.assertNotIn("or central", label)

    def test_orders_oauth_scopes_and_commerce_writes_are_exact(self):
        orders = SURFACE["operations"]["temperaDropshipping"]
        oauth_only_scopes = {"orders:read", "orders:commerce:write"}
        oauth_only_operations = [operation for operation in orders if operation.get("scope") in oauth_only_scopes]
        self.assertTrue(oauth_only_operations)
        for operation in oauth_only_operations:
            with self.subTest(operation=operation["id"]):
                self.assertIn("cannot carry", generator.auth_label(SURFACE, "temperaDropshipping", operation))

        commerce_write_operations = {
            operation["id"] for operation in orders if operation.get("scope") == "orders:commerce:write"
        }
        self.assertEqual(commerce_write_operations, {"createCatalogOffer", "createSaleOrder"})

        merchant_read = next(operation for operation in SURFACE["operations"]["temperaPayments"] if operation["id"] == "getMerchant")
        self.assertIn("or central", generator.auth_label(SURFACE, "temperaPayments", merchant_read))

    def test_generated_auth_page_describes_fallback_without_promising_eligibility(self):
        # Verify actual committed generated output, not only a formatter helper.
        page = (generator.SITE / "authentication.mdx").read_text()
        self.assertIn("Orders reads require an expiring OAuth", page)
        self.assertIn("OAuth-only operations reject API-key requests", page)
        self.assertNotIn("work as bearers at every product", page)


if __name__ == "__main__":
    unittest.main()
