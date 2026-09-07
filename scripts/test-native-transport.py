#!/usr/bin/env python3
"""Focused regression tests for the bounded native transport allowlist."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts/check-native-transport.py"
spec = importlib.util.spec_from_file_location("native_transport_checker", CHECKER_PATH)
assert spec and spec.loader
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def synthetic_contract() -> dict:
    return {
        "operations": [
            {
                "operation": f"temperaPayments.{operation['id']}",
                "method": operation["method"],
                "pathTemplate": operation["path"],
                "pathShape": checker.path_shape(operation["path"]),
            }
            for operation in checker.PAYMENTS_NATIVE_OPERATIONS
        ]
    }


class NativeTransportTests(unittest.TestCase):
    def test_only_five_payment_merchant_operations_are_admitted(self) -> None:
        operations = checker.PAYMENTS_NATIVE_OPERATIONS
        self.assertEqual(
            [operation["id"] for operation in operations],
            [
                "getWorkspaceMerchant",
                "createMerchant",
                "getMerchant",
                "refreshMerchantEligibility",
                "createMerchantOnboardingLink",
            ],
        )
        self.assertNotIn("createPaymentIntent", [operation["id"] for operation in operations])
        self.assertEqual(
            {operation["scope"] for operation in operations},
            {"payments:merchants:read", "payments:merchants:write"},
        )

    def test_wrong_payment_scope_is_rejected_against_producer_metadata(self) -> None:
        operation = dict(checker.PAYMENTS_NATIVE_OPERATIONS[0])
        upstream = {
            "_method": operation["method"],
            "_path": operation["path"],
            "x-tempera-auth-audience": "tempera-payments",
            "x-tempera-required-scope": "payments:merchants:write",
        }
        with self.assertRaisesRegex(ValueError, "scope drifts"):
            checker.validate_payment_mapping(operation, upstream)

    def test_existing_business_and_orders_contract_operations_remain_admitted(self) -> None:
        surface = json.loads((ROOT / "surface.json").read_text(encoding="utf-8"))
        contract = json.loads(
            (ROOT / "contracts/native-transport-v1.json").read_text(encoding="utf-8")
        )
        for product in ("temperaBusiness", "temperaDropshipping"):
            expected = {
                f"{product}.{operation['id']}"
                for operation in surface["operations"][product]
            }
            actual = {
                operation["operation"]
                for operation in contract["operations"]
                if operation["product"] == product
            }
            self.assertEqual(actual, expected)

    def test_merchant_routes_must_be_annotated_with_exact_method_and_path(self) -> None:
        contract = synthetic_contract()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = root / "Good.swift"
            good.write_text(
                "\n".join(
                    [
                        "// tempera-transport: temperaPayments.getWorkspaceMerchant GET /v1/merchants",
                        'let a = "/v1/merchants"',
                        "// tempera-transport: temperaPayments.createMerchant POST /v1/merchants",
                        'let b = "/v1/merchants"',
                        "// tempera-transport: temperaPayments.getMerchant GET /v1/merchants/{merchant_id}",
                        'let c = "/v1/merchants/\\(id)"',
                        "// tempera-transport: temperaPayments.refreshMerchantEligibility POST /v1/merchants/{merchant_id}/refresh",
                        'let d = "/v1/merchants/\\(id)/refresh"',
                        "// tempera-transport: temperaPayments.createMerchantOnboardingLink POST /v1/merchants/{merchant_id}/onboarding",
                        'let e = "/v1/merchants/\\(id)/onboarding"',
                    ]
                )
                + "\n"
            )
            self.assertEqual(checker.check_client(good, contract), [])

            unannotated = root / "Unannotated.swift"
            unannotated.write_text('let route = "/v1/merchants/\\(id)/refresh"\n')
            self.assertTrue(
                any(
                    "undeclared canonical route" in failure
                    for failure in checker.check_client(unannotated, contract)
                )
            )

            wrong_method = root / "WrongMethod.swift"
            wrong_method.write_text(
                "// tempera-transport: temperaPayments.getMerchant POST /v1/merchants/{merchant_id}\n"
                'let route = "/v1/merchants/\\(id)"\n'
            )
            self.assertTrue(
                any(
                    "declares POST" in failure
                    for failure in checker.check_client(wrong_method, contract)
                )
            )


if __name__ == "__main__":
    unittest.main()
