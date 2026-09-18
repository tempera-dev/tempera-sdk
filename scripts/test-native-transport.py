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
    def test_only_six_payment_merchant_operations_are_admitted(self) -> None:
        operations = checker.PAYMENTS_NATIVE_OPERATIONS
        self.assertEqual(
            [operation["id"] for operation in operations],
            [
                "getMerchantWorkspace",
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

    def test_required_idempotency_headers_are_bound_to_producer(self) -> None:
        spec = json.loads((ROOT / "specs/tempera-payments.openapi.json").read_text())
        upstream = checker.upstream_operations(spec)
        for operation in checker.PAYMENTS_NATIVE_OPERATIONS:
            if operation["scope"] != "payments:merchants:write":
                continue
            self.assertEqual(operation["requiredHeaders"], ["Idempotency-Key"])
            original = upstream[operation["upstreamOperationId"]]
            checker.validate_payment_mapping(operation, original)
            for poisoned in ({**original, "_headers": []}, {**original, "_headers": [{"name": "Idempotency-Key", "in": "header", "required": False}]}):
                with self.assertRaisesRegex(ValueError, "headers drift"):
                    checker.validate_payment_mapping(operation, poisoned)

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

    def test_workflows_publishes_reads_and_never_a_run_start(self) -> None:
        contract = json.loads(
            (ROOT / "contracts/native-transport-v1.json").read_text(encoding="utf-8")
        )
        published = [
            operation
            for operation in contract["operations"]
            if operation["product"] == "temperaWorkflows"
        ]
        self.assertEqual(
            sorted(operation["id"] for operation in published),
            ["getRun", "getWorkflow", "listRuns", "listWorkflows"],
        )
        self.assertEqual({operation["method"] for operation in published}, {"GET"})
        self.assertEqual({operation["safeRetry"] for operation in published}, {"read"})
        self.assertEqual({operation["scope"] for operation in published}, {"workflow:read"})
        self.assertEqual(
            {operation["authAudience"] for operation in published}, {"tempera-workflows"}
        )
        upstream = {operation["upstreamOperationId"] for operation in published}
        self.assertEqual(upstream, {"workflows.list", "workflows.get", "runs.list", "runs.get"})
        self.assertFalse(upstream & {"runs.create", "workflows.call", "runs.cancel"})

    def test_workflow_run_start_is_not_admitted_to_a_device(self) -> None:
        surface = json.loads((ROOT / "surface.json").read_text(encoding="utf-8"))
        run_scoped = {
            operation["id"]
            for operation in surface["operations"]["temperaWorkflows"]
            if operation.get("scope") in {"workflow:run", "workflow:write"}
        }
        self.assertIn("createRun", run_scoped)
        self.assertFalse(run_scoped & checker.NATIVE_OPERATIONS["temperaWorkflows"])
        contract = json.loads(
            (ROOT / "contracts/native-transport-v1.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Runs.swift"
            source.write_text(
                "// tempera-transport: temperaWorkflows.createRun POST /v1/workflows/{workflowId}/runs\n"
                'let route = "/v1/workflows/\\(id)/runs"\n'
            )
            failures = checker.check_client(source, contract)
        self.assertTrue(
            any("is not an admitted native operation" in failure for failure in failures),
            failures,
        )

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
                        "// tempera-transport: temperaPayments.getMerchant GET /v1/merchants/{merchantId}",
                        'let c = "/v1/merchants/\\(id)"',
                        "// tempera-transport: temperaPayments.refreshMerchantEligibility POST /v1/merchants/{merchantId}/refresh",
                        'let d = "/v1/merchants/\\(id)/refresh"',
                        "// tempera-transport: temperaPayments.createMerchantOnboardingLink POST /v1/merchants/{merchantId}/onboarding",
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
                    "undeclared temperaPayments route" in failure
                    for failure in checker.check_client(unannotated, contract)
                )
            )

            wrong_method = root / "WrongMethod.swift"
            wrong_method.write_text(
                "// tempera-transport: temperaPayments.getMerchant POST /v1/merchants/{merchantId}\n"
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
