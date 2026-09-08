#!/usr/bin/env python3
"""Exercise Swift commerce creation against the exact local Orders producer over TCP."""
import argparse
import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "swift-commerce-test-token"
PREFIX = "/v1/organizations/fixture-org/projects/fixture-project/environments/test/sites/fixture-site"
TABLES = ("resources", "history", "audit", "events", "event_projections", "commerce_replays")
EXPECTED_SOURCE = {
    "source_repo": "tempera-dev/tempera-dropshipping",
    "source_branch": "main",
    "source_path": "contracts/openapi/dropshipping.openapi.json",
}


def fail(message):
    raise SystemExit(message)


def git(source, *parts):
    return subprocess.check_output(["git", "-C", str(source), *parts], text=True).strip()


def validate_source(source):
    lock_path = ROOT / "specs/tempera-dropshipping-api.json.source"
    lock = json.loads(lock_path.read_text())
    if any(lock.get(key) != value for key, value in EXPECTED_SOURCE.items()):
        fail("Orders source identity is not allowlisted")
    if git(source, "rev-parse", "HEAD") != lock["source_commit"]:
        fail("A clean checkout at the exact SDK Orders source commit is required")
    if git(source, "status", "--porcelain"):
        fail("A clean checkout at the exact SDK Orders source commit is required")
    contract = source / lock["source_path"]
    if not contract.is_file() or hashlib.sha256(contract.read_bytes()).hexdigest() != lock["source_sha256"]:
        fail("Source contract digest mismatch")
    return lock


def snapshot(database):
    with sqlite3.connect(database) as db:
        return {
            table: db.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
            for table in TABLES
        }


def assert_two_declared_rows(snapshot_value):
    counts = {table: len(rows) for table, rows in snapshot_value.items()}
    if counts != {table: 2 for table in TABLES}:
        raise AssertionError(f"expected exactly two durable commerce rows per table, got {counts}")


class ProducerServer:
    def __init__(self, app, receipts):
        self.socket = socket.socket()
        self.socket.bind(("127.0.0.1", 0))
        self.port = self.socket.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(app, log_level="error", ws="none", access_log=False))
        self.worker = threading.Thread(target=self.server.run, kwargs={"sockets": [self.socket]}, daemon=True)
        self.receipts = receipts

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}"

    def start(self):
        self.worker.start()
        deadline = time.monotonic() + 5
        while not self.server.started and self.worker.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not self.server.started:
            self.close()
            raise AssertionError("Orders Uvicorn did not start")

    def close(self):
        self.server.should_exit = True
        self.worker.join(timeout=5)
        try:
            self.socket.close()
        finally:
            if self.worker.is_alive():
                raise AssertionError("Orders Uvicorn did not stop")


def app_for(source, database, receipts, request_bodies):
    sys.path.insert(0, str(source / "src"))
    from tempera_dropshipping.api import create_app
    from tempera_dropshipping.models import Scope

    scope = Scope(organization_id="fixture-org", project_id="fixture-project", environment="test", site_id="fixture-site")
    principal = {"subject": "swift-commerce-fixture", "scope": scope,
                 "permissions": {"orders:read", "orders:commerce:write"}}
    now = datetime(2026, 9, 7, 12, 34, 56, 123456, tzinfo=timezone.utc)
    app = create_app(database=database, clock=lambda: now,
                     authenticator=lambda token: principal if token == TOKEN else None)

    @app.middleware("http")
    async def receipt(request, call_next):
        if request.method == "POST" and request.url.path in {
            PREFIX + "/catalog/offers", PREFIX + "/sale-orders"
        }:
            try:
                request_bodies.append(json.loads((await request.body()).decode("utf-8")))
            except (UnicodeDecodeError, json.JSONDecodeError):
                request_bodies.append(None)
        response = await call_next(request)
        if request.url.path.startswith(PREFIX):
            receipts.append((request.method, request.url.path, response.status_code))
        return response

    return app


def compile_driver(build_dir, driver):
    source_dir = ROOT / "packages/swift/Sources/TemperaMerchantSDK"
    swift_files = sorted(source_dir.glob("*.swift"))
    if not swift_files:
        fail("TemperaMerchantSDK Swift sources are missing")
    if not driver.is_file():
        fail("Swift commerce creation driver is missing")
    build_dir.mkdir(parents=True, exist_ok=True)
    module = build_dir / "TemperaMerchantSDK.swiftmodule"
    library = build_dir / "libTemperaMerchantSDK.dylib"
    subprocess.run([
        "swiftc", "-swift-version", "6", "-enable-testing", "-emit-library", "-emit-module",
        "-module-name", "TemperaMerchantSDK", *map(str, swift_files), "-o", str(library),
        "-emit-module-path", str(module),
    ], check=True)
    executable = build_dir / "verify-swift-commerce-creation"
    subprocess.run([
        "swiftc", "-swift-version", "6", "-parse-as-library", "-I", str(build_dir), "-L", str(build_dir),
        "-lTemperaMerchantSDK", str(driver), "-o", str(executable),
    ], check=True)
    return executable


def invoke(driver, *arguments):
    result = subprocess.run([str(driver), *arguments], check=True, text=True,
                            capture_output=True, timeout=120, env={**os.environ, "NO_PROXY": "*"})
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError("Swift driver did not emit one JSON result") from error
    if not isinstance(value, dict):
        raise AssertionError("Swift driver result must be a JSON object")
    return value


def expect_receipts(receipts, order_id):
    expected_paths = {
        "offer": PREFIX + "/catalog/offers",
        "sale": PREFIX + "/sale-orders",
    }
    expected = [
        ("POST", expected_paths["offer"], 201),
        ("POST", expected_paths["sale"], 201),
        ("POST", expected_paths["sale"], 200),
        ("GET", expected_paths["sale"] + "/"),
        ("POST", expected_paths["sale"], 409),
    ]
    if len(receipts) != len(expected):
        raise AssertionError(f"expected five commerce receipts, got {receipts}")
    if receipts[0] != expected[0] or receipts[1] != expected[1] or receipts[2] != expected[2] or receipts[4] != expected[4]:
        raise AssertionError(f"unexpected create/replay receipts: {receipts}")
    method, path, status = receipts[3]
    if method != "GET" or path != expected_paths["sale"] + "/" + order_id or status != 200:
        raise AssertionError(f"unexpected recovery read receipt: {receipts}")


def assert_public_request_bodies(request_bodies):
    """Prove the SDK spoke the producer's lowerCamelCase public JSON wire."""
    if len(request_bodies) != 4 or any(not isinstance(body, dict) for body in request_bodies):
        raise AssertionError("expected four decodable commerce request bodies")
    offer, *sales = request_bodies
    required_offer = {
        "merchantId", "productClassification", "name", "description", "currency",
        "unitAmountMinor",
    }
    if not required_offer.issubset(offer) or any(
        key in offer for key in (
            "merchant_id", "product_classification", "photo_url", "unit_amount_minor",
            "expires_at",
        )
    ):
        raise AssertionError("offer request did not use the public lowerCamelCase wire")
    if any(
        set(body) != {"offerId", "offerRevision", "quantity"}
        for body in sales
    ):
        raise AssertionError("sale request did not use the public lowerCamelCase wire")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", required=True, type=Path)
    parser.add_argument("--build-dir", required=True, type=Path)
    parser.add_argument("--driver", type=Path, default=ROOT / "scripts/verify-swift-commerce-creation.swift")
    args = parser.parse_args()
    source = args.source_repo.resolve()
    lock = validate_source(source)
    driver = compile_driver(args.build_dir.resolve(), args.driver.resolve())

    receipts = []
    request_bodies = []
    with tempfile.TemporaryDirectory(prefix="swift-commerce-producer-") as directory:
        database = Path(directory) / "orders.sqlite"
        first = ProducerServer(app_for(source, database, receipts, request_bodies), receipts)
        first.start()
        try:
            prepared = invoke(driver, "prepare", first.url)
        finally:
            first.close()
        offer_id = prepared.get("offer_id")
        if not isinstance(offer_id, str) or not offer_id:
            raise AssertionError("Swift prepare did not return offer_id")
        before = snapshot(database)
        assert_two_declared_rows(before)

        second = ProducerServer(app_for(source, database, receipts, request_bodies), receipts)
        second.start()
        try:
            recovered = invoke(driver, "recover", second.url, offer_id)
        finally:
            second.close()
        if not isinstance(recovered.get("order_id"), str) or recovered.get("amount_minor") != 3600:
            raise AssertionError("Swift recovery did not return the replayed order and authoritative amount")
        with sqlite3.connect(database) as db:
            records = {kind: json.loads(payload) for kind, payload in db.execute("SELECT kind,payload FROM resources")}
        if set(records) != {"catalog_offer", "sale_order"}:
            raise AssertionError("expected one offer and one sale order")
        offer, order = records["catalog_offer"], records["sale_order"]
        if (offer["id"] != offer_id or order["id"] != recovered["order_id"] or
                order["offer_id"] != offer["id"] or order["merchant_id"] != offer["merchant_id"] or
                offer["unit_amount_minor"] != 1200 or order["quantity"] != 3 or order["amount_minor"] != 3600):
            raise AssertionError("persisted offer/order identity or independently computed amount differs")
        after = snapshot(database)
        if after != before:
            raise AssertionError("recovery, GET, or conflicting idempotency retry changed durable producer state")

    expect_receipts(receipts, recovered["order_id"])
    assert_public_request_bodies(request_bodies)
    statuses = [status for _, _, status in receipts]
    print(f"PASS: Orders {lock['source_commit']} statuses={statuses}; 2 durable declared records; replay state unchanged")


if __name__ == "__main__":
    main()
