import Foundation
import XCTest

@testable import TemperaSDK

/// Behaviour 5: the `google.rpc.Status` cascade every product error folds into,
/// mirroring `packages/rust/src/error.rs::normalize_error_body` and
/// `test_http_errors_normalize_every_fleet_wire_shape` in the Python suite.
final class ErrorNormalizationTests: XCTestCase {
    private func normalize(_ body: String, statusText: String = "") -> TemperaNormalizedError {
        TemperaApiError.normalize(body: TemperaJSON.parse(body), statusText: statusText)
    }

    func testCanonicalAip193EnvelopePrefersTheStringStatusOverTheIntegerCode() {
        let normalized = normalize(
            """
            {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "Bad envelope.",
             "requestId": "req-de-1",
             "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo",
                          "reason": "MALFORMED_ENVELOPE", "domain": "data-engine"}]}}
            """,
            statusText: "Bad Request"
        )
        XCTAssertEqual(normalized.code, "INVALID_ARGUMENT")
        XCTAssertEqual(normalized.message, "Bad envelope.")
        XCTAssertEqual(normalized.reason, "MALFORMED_ENVELOPE")
        XCTAssertEqual(normalized.requestId, "req-de-1")
    }

    func testIntegerCodeAloneNeverBecomesTheCode() {
        // `error.code` counts only when it is a string; an integer code is the
        // HTTP status repeated, which callers must not branch on.
        let normalized = normalize(#"{"error":{"code":404,"message":"gone"}}"#, statusText: "Not Found")
        XCTAssertNil(normalized.code)
        XCTAssertEqual(normalized.message, "gone")
    }

    func testLegacyNestedShapeExtractsCodeMessageAndRequestId() {
        let normalized = normalize(
            """
            {"error": {"code": "lane_unavailable", "message": "no python lane",
             "status": 503, "request_id": "req_123", "retryable": true}}
            """,
            statusText: "Service Unavailable"
        )
        XCTAssertEqual(normalized.code, "lane_unavailable")
        XCTAssertEqual(normalized.message, "no python lane")
        XCTAssertEqual(normalized.requestId, "req_123")
        XCTAssertNil(normalized.reason)
    }

    func testLegacyFlatShapeUsesErrorAsCodeAndMessageAsMessage() {
        let normalized = normalize(#"{"error":"invalid_token","message":"token expired"}"#)
        XCTAssertEqual(normalized.code, "invalid_token")
        XCTAssertEqual(normalized.message, "token expired")
        XCTAssertNil(normalized.requestId)
    }

    func testLegacyMessageOnlyShapeHasNoCode() {
        let normalized = normalize(#"{"error":"session is drained"}"#)
        XCTAssertNil(normalized.code)
        XCTAssertEqual(normalized.message, "session is drained")
    }

    func testErrorObjectWithoutAMessageFallsBackToTheStatusText() {
        let normalized = normalize(#"{"error":{"code":"opaque"}}"#, statusText: "Internal Server Error")
        XCTAssertEqual(normalized.code, "opaque")
        XCTAssertEqual(normalized.message, "Internal Server Error")
    }

    func testUnparseableAndUnknownBodiesFallBackToTheStatusText() {
        for body in ["<html>bad gateway</html>", #"{"error":"boom"#, "", "   \n "] {
            let normalized = normalize(body, statusText: "Bad Gateway")
            XCTAssertNil(normalized.code, body)
            XCTAssertEqual(normalized.message, "Bad Gateway", body)
        }
        XCTAssertEqual(normalize(#"{"ok":false}"#, statusText: "Boom").message, "Boom")
        XCTAssertEqual(normalize(#"{"error":42}"#, statusText: "Boom").message, "Boom")
        XCTAssertEqual(normalize("", statusText: "").message, "request failed")
    }

    func testSurrogatePairsAndEscapesSurviveNormalization() {
        let normalized = normalize(
            #"{"error":"bad_input","message":"field \"name\" is bad\n\ttab \\ slash \/ u: é 😀"}"#
        )
        XCTAssertEqual(normalized.code, "bad_input")
        XCTAssertEqual(
            normalized.message, "field \"name\" is bad\n\ttab \\ slash / u: \u{e9} \u{1F600}")
    }

    func testRequestIdFallsBackToTheXRequestIdResponseHeader() {
        let error = TemperaApiError.from(
            status: 500,
            statusText: "Internal Server Error",
            headers: [TemperaKeyValue(key: "X-Request-Id", value: "req_from_header")],
            body: TemperaJSON.parse(#"{"error":{"code":"boom","message":"kaput"}}"#),
            product: "palette",
            operation: "listTraces"
        )
        XCTAssertEqual(error.requestId, "req_from_header")
        XCTAssertEqual(error.code, "boom")
        XCTAssertEqual(error.message, "Tempera palette.listTraces failed (500): kaput")

        // A body request id wins over the header.
        let fromBody = TemperaApiError.from(
            status: 500,
            headers: [TemperaKeyValue(key: "x-request-id", value: "req_from_header")],
            body: TemperaJSON.parse(#"{"error":{"message":"kaput","request_id":"req_from_body"}}"#)
        )
        XCTAssertEqual(fromBody.requestId, "req_from_body")
        XCTAssertEqual(fromBody.message, "Tempera request failed (500): kaput")
    }

    func testDispatchedErrorsCarryProductAndOperationContext() async throws {
        let transport = StubTransport(responder: { _, _ in
            TemperaHTTPResponse(
                status: 404,
                headers: [
                    TemperaKeyValue(key: "content-type", value: "application/json"),
                    TemperaKeyValue(key: "x-request-id", value: "req_1"),
                ],
                body: Data(#"{"error":{"status":"NOT_FOUND","message":"no such trace"}}"#.utf8)
            )
        })
        let client = try TestFixtures.client(transport: transport)
        do {
            try await client.palette.call("listTraces", ["tenantId": "acme"])
            XCTFail("expected a TemperaApiError")
        } catch let error as TemperaApiError {
            XCTAssertEqual(error.status, 404)
            XCTAssertEqual(error.code, "NOT_FOUND")
            XCTAssertEqual(error.product, "palette")
            XCTAssertEqual(error.operation, "listTraces")
            XCTAssertEqual(error.requestId, "req_1")
            XCTAssertEqual(error.message, "Tempera palette.listTraces failed (404): no such trace")
        }
    }

    func testTransportFailuresSurfaceAsConnectionErrors() async throws {
        let transport = StubTransport(responder: { _, _ in
            throw TemperaTransportError("connection reset")
        })
        let client = try TestFixtures.client(transport: transport)
        do {
            try await client.palette.call("listTraces", ["tenantId": "acme"])
            XCTFail("expected a TemperaTransportError")
        } catch let error as TemperaTransportError {
            XCTAssertEqual(error.description, "Tempera connection failed: connection reset")
        }
    }
}
