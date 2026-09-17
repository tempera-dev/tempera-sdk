import Foundation
import XCTest

@testable import TemperaSDK

/// The conformance loop: every generated operation is dispatched against a
/// stubbed transport, and the request it produces is checked field by field.
/// This mirrors `packages/python/tests/test_client.py::ConformanceTest` and
/// the Rust `builds_every_operation_in_the_surface_tables` test.
final class SurfaceConformanceTests: XCTestCase {
    func testEverySurfaceOperationDispatchesMethodPathAuthAndBody() async throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)

        for op in TemperaSurface.operations {
            let label = "\(op.product).\(op.id)"
            await transport.clear()

            XCTAssertFalse(op.upstreamOperationId.isEmpty, "\(label) producer operation id")

            var params = TemperaParams()
            for name in op.pathParams {
                params.set(name, .string(TestFixtures.pathParam(op, name)))
            }
            for name in op.requiredQuery {
                params.set(name, .string(TestFixtures.sampleQueryValue))
            }
            let content: Data? = op.requestBodyKind == "binary" ? Data([1, 2, 3]) : nil

            let result = try await client.call(
                op.product, op.id, params, content: content)
            XCTAssertEqual(result["ok"], .bool(true), "\(label) result")

            let requests = await transport.requests
            XCTAssertEqual(requests.count, 1, "\(label) made one request")
            guard let recorded = requests.first else { continue }
            let parts = RequestParts(recorded)

            XCTAssertEqual(parts.method, op.method, "\(label) method")
            XCTAssertEqual(parts.origin, TestFixtures.baseUrl(op.product), "\(label) origin")
            XCTAssertEqual(parts.path, TestFixtures.expectedPath(op), "\(label) path")
            XCTAssertEqual(parts.headers["accept"], "application/json", "\(label) accept")

            switch op.auth {
            case "none":
                XCTAssertNil(parts.headers["authorization"], "\(label) sends no bearer")
            case "account":
                XCTAssertEqual(
                    parts.headers["authorization"], "Bearer \(TestFixtures.accountToken)",
                    "\(label) account bearer")
            case "introspectionSecret":
                XCTAssertEqual(
                    parts.headers["authorization"], "Bearer \(TestFixtures.introspectionSecret)",
                    "\(label) introspection bearer")
            case "product", "oauthResource":
                XCTAssertEqual(
                    parts.headers["authorization"], "Bearer \(TestFixtures.apiKey)",
                    "\(label) product bearer")
            default:
                XCTFail("\(label) unexpected auth kind \(op.auth)")
            }

            if op.requestBodyKind == "binary" {
                XCTAssertEqual(
                    parts.headers["content-type"], op.requestContentType, "\(label) content type")
                XCTAssertEqual(parts.rawBody, Data([1, 2, 3]), "\(label) binary body")
            } else if op.body.isEmpty, op.bodyDefaults.isEmpty {
                XCTAssertNil(parts.rawBody, "\(label) sends no body")
                XCTAssertNil(parts.headers["content-type"], "\(label) declares no content type")
            } else {
                XCTAssertEqual(
                    parts.headers["content-type"], "application/json", "\(label) content type")
                for pair in op.bodyDefaults {
                    XCTAssertEqual(
                        parts.body?[pair.key], .string(pair.value),
                        "\(label) body default \(pair.key)")
                }
            }

            for key in op.requiredQuery {
                XCTAssertEqual(
                    parts.query[key], TestFixtures.sampleQueryValue,
                    "\(label) required query \(key)")
            }
        }
    }

    func testGeneratedTablesMatchTheManifestShape() {
        // Counts are deliberately not hard-coded: this table is regenerated
        // every time a producer publishes a route.
        XCTAssertGreaterThan(TemperaSurface.operations.count, 0)
        XCTAssertGreaterThan(TemperaSurface.products.count, 0)
        XCTAssertGreaterThan(TemperaSurface.environments.count, 0)
        XCTAssertFalse(TemperaSurface.audiences.isEmpty)
        XCTAssertTrue(TemperaSurface.audiences.contains(TemperaSurface.defaultAudience))
        XCTAssertEqual(TemperaSDK.surfaceVersion, TemperaSurface.version)
        XCTAssertEqual(TemperaSDK.version, "0.13.0")

        // Every operation belongs to a registered product, names a registered
        // audience when it pins one, and carries a known retry classification.
        for op in TemperaSurface.operations {
            XCTAssertNotNil(
                TemperaSurface.findProduct(key: op.product), "\(op.product) is registered")
            XCTAssertNotNil(
                TemperaSurface.findOperation(product: op.product, id: op.id),
                "\(op.product).\(op.id) is findable")
            if let audience = op.authAudience {
                XCTAssertTrue(
                    TemperaSurface.audiences.contains(audience),
                    "\(op.product).\(op.id) audience \(audience)")
            }
            XCTAssertTrue(
                ["read", "idempotent", "none"].contains(op.safeRetry),
                "\(op.product).\(op.id) safeRetry")
            XCTAssertTrue(
                ["none", "account", "product", "oauthResource", "introspectionSecret"]
                    .contains(op.auth),
                "\(op.product).\(op.id) auth")
        }

        // The flat table is partitioned by product, exactly like the Rust one.
        let counted = TemperaSurface.products.reduce(0) {
            $0 + TemperaSurface.operationsFor(product: $1.key).count
        }
        XCTAssertEqual(counted, TemperaSurface.operations.count)
    }

    func testProductAccessorsCoverEveryRegisteredProduct() throws {
        let transport = StubTransport()
        let client = try TestFixtures.client(transport: transport)
        for spec in TemperaSurface.products {
            let product = try client.product(spec.key)
            XCTAssertEqual(product.key, spec.key)
            XCTAssertEqual(product.envVar, spec.envVar)
            XCTAssertEqual(product.audience, spec.audience)
            XCTAssertEqual(product.description, spec.description)
            XCTAssertEqual(
                product.operations.count, TemperaSurface.operationsFor(product: spec.key).count)
        }
        // The generated convenience accessors resolve to the same clients.
        XCTAssertEqual(client.palette.key, "palette")
        XCTAssertEqual(client.controlPlane.key, "controlPlane")
        XCTAssertEqual(client.dataEngine.key, "dataEngine")
        XCTAssertEqual(client.tempOS.key, "tempOS")
    }
}
