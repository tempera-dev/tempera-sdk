#!/usr/bin/env python3
"""Capture real local Orders HTTP responses at the SDK's exact reviewed source lock."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source = args.source_repo.resolve()
    lock = json.loads((ROOT / "specs/tempera-dropshipping-api.json.source").read_text())
    def git(*parts):
        return subprocess.check_output(["git", "-C", str(source), *parts], text=True).strip()
    if git("rev-parse", "HEAD") != lock["source_commit"] or git("status", "--porcelain"):
        raise SystemExit("A clean checkout at the exact SDK Orders source commit is required")
    if hashlib.sha256((source / lock["source_path"]).read_bytes()).hexdigest() != lock["source_sha256"]:
        raise SystemExit("Source contract digest mismatch")
    sys.path.insert(0, str(source / "src"))
    from fastapi.testclient import TestClient
    from tempera_dropshipping.api import create_app
    from tempera_dropshipping.models import Scope
    scope = Scope(organization_id="fixture-org", project_id="fixture-project", environment="test", site_id="fixture-site")
    principal = {"subject": "fixture-human", "scope": scope,
                 "permissions": {"orders:read", "orders:write"}}
    now = datetime(2026, 9, 7, 12, 34, 56, 123456, tzinfo=timezone.utc)
    prefix = "/v1/organizations/fixture-org/projects/fixture-project/environments/test/sites/fixture-site"
    headers = {"Authorization": "Bearer synthetic-fixture-token", "Idempotency-Key": "swift-offer-fixture-key"}
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(database=Path(directory) / "orders.sqlite", clock=lambda: now,
                         authenticator=lambda token: principal if token == "synthetic-fixture-token" else None)
        with TestClient(app) as client:
            ids = iter([uuid.UUID("00000000-0000-4000-8000-000000000001"), uuid.UUID("00000000-0000-4000-8000-000000000002")])
            with patch("tempera_dropshipping.service.uuid", SimpleNamespace(uuid4=lambda: next(ids))):
                response = client.post(prefix + "/catalog/offers", headers=headers, json={
                    "merchant_id": "12345678-1234-4123-8123-123456789abc", "product_classification": "offline_services",
                    "name": "Fixture service", "description": "An actual local declaration", "currency": "USD", "unit_amount_minor": 1200})
                assert response.status_code == 201, response.text
                offer = response.json()
                response = client.post(prefix + "/sale-orders", headers={**headers, "Idempotency-Key": "swift-order-fixture-key"},
                    json={"offer_id": offer["id"], "offer_revision": 1, "quantity": 3})
                assert response.status_code == 201, response.text
                order = response.json()
            responses = {}
            for name, path in (("offer", "/catalog/offers/" + offer["id"]), ("offers", "/catalog/offers"),
                               ("order", "/sale-orders/" + order["id"]), ("orders", "/sale-orders")):
                response = client.get(prefix + path, headers=headers)
                assert response.status_code == 200, response.text
                responses[name] = response.json()
    output = {"source_commit": lock["source_commit"], "source_sha256": lock["source_sha256"],
              "qualification": "ACTUAL_LOCAL_HTTP_DECLARATIONS_ONLY", "responses": responses}
    expected = (json.dumps(output, indent=2, sort_keys=True) + "\n").encode()
    path = ROOT / "packages/swift/Tests/TemperaMerchantSDKTests/Fixtures/orders-commerce.json"
    if args.check:
        if path.read_bytes() != expected:
            raise SystemExit("Swift commerce fixture differs from actual producer")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(expected)
    print("PASS: exact-source actual local Orders HTTP commerce fixture")


if __name__ == "__main__":
    main()
