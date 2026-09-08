// Uniform Tempera SDK errors, shared in shape with the TypeScript, Python,
// Rust, and Kotlin packages (see `surface.json` `errorContract`).
//
// - `TemperaSdkError`: a configuration or usage mistake, caught before or
//   instead of a request (missing credential, unknown product, bad path
//   parameter).
// - `TemperaApiError`: an HTTP response error, normalized from the canonical
//   AIP-193 envelope and the supported compatibility shapes so callers always
//   read the same fields.
// - `TemperaMcpError`: a JSON-RPC error from the MCP gateway.
// - `TemperaTransportError`: the request never produced an HTTP response.

import Foundation

/// Every error this package throws.
public protocol TemperaFailure: Error, Sendable {
    /// Human-readable description; never empty.
    var message: String { get }
}

/// A configuration or usage mistake, raised before a request is sent.
public struct TemperaSdkError: TemperaFailure, Equatable, CustomStringConvertible {
    /// What went wrong.
    public let message: String

    /// Create one usage error.
    public init(_ message: String) {
        self.message = message
    }

    public var description: String { message }
}

/// The request never produced an HTTP response (DNS, TLS, timeout, reset).
public struct TemperaTransportError: TemperaFailure, Equatable, CustomStringConvertible {
    /// What the underlying transport reported.
    public let message: String

    /// Create one transport error.
    public init(_ message: String) {
        self.message = message
    }

    public var description: String { "Tempera connection failed: \(message)" }
}

/// A JSON-RPC error returned by the MCP gateway.
public struct TemperaMcpError: TemperaFailure, Equatable, CustomStringConvertible {
    /// JSON-RPC error code; `0` when the response carried no integer code.
    public let code: Int
    /// Human-readable error message.
    public let message: String
    /// The error's `data` member, when it carried one.
    public let data: TemperaJSON?

    /// Create one MCP error.
    public init(code: Int, message: String, data: TemperaJSON? = nil) {
        self.code = code
        self.message = message
        self.data = data
    }

    public var description: String { "MCP error \(code): \(message)" }
}

/// The uniform fields every Tempera error body normalizes to.
public struct TemperaNormalizedError: Sendable, Equatable {
    /// Machine-readable code, when the wire shape carried one.
    public let code: String?
    /// Human-readable message; never empty.
    public let message: String
    /// AIP-193 `google.rpc.ErrorInfo` reason from `error.details[]`.
    public let reason: String?
    /// Server request id carried in the body.
    public let requestId: String?
}

/// An HTTP response error with the uniform Tempera error fields.
public struct TemperaApiError: TemperaFailure, Equatable, CustomStringConvertible {
    /// HTTP status code of the failed response.
    public let status: Int
    /// Machine-readable error code, when the wire shape carried one.
    public let code: String?
    /// Human-readable message, already labelled with product and operation.
    public let message: String
    /// AIP-193 `google.rpc.ErrorInfo` reason. Producers publish a closed reason
    /// vocabulary, so this is the field to branch on.
    public let reason: String?
    /// Server request id, from the body or the `x-request-id` header.
    public let requestId: String?
    /// Product key that made the request.
    public let product: String?
    /// Operation id that made the request.
    public let operation: String?
    /// The parsed response body, when it was JSON.
    public let body: TemperaJSON?
    /// The HTTP status text, kept so the error can be re-labelled later.
    public let statusText: String

    /// Create one API error.
    public init(
        status: Int,
        code: String? = nil,
        message: String,
        reason: String? = nil,
        requestId: String? = nil,
        product: String? = nil,
        operation: String? = nil,
        body: TemperaJSON? = nil,
        statusText: String = ""
    ) {
        self.status = status
        self.code = code
        self.message = message
        self.reason = reason
        self.requestId = requestId
        self.product = product
        self.operation = operation
        self.body = body
        self.statusText = statusText
    }

    public var description: String { message }

    /// Return the AIP-193 `google.rpc.ErrorInfo` reason from an error's
    /// `details[]`. The first detail carrying a string `reason` wins.
    public static func errorInfoReason(_ error: TemperaJSON) -> String? {
        guard let details = error["details"]?.arrayValue else { return nil }
        for detail in details {
            if let reason = detail["reason"]?.stringValue { return reason }
        }
        return nil
    }

    /// Normalize any Tempera product error body into the uniform fields.
    ///
    /// Wire shapes handled (see `surface.json` `errorContract.wireShapes`):
    /// - canonical resource API:
    ///   `{"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "...", "details": []}}`
    /// - legacy flat: `{"error": "<code>", "message": "<text>"}`
    /// - legacy message-only: `{"error": "<human message>"}`
    /// - legacy nested: `{"error": {"code", "message", "request_id"?, ...}}`
    /// - anything else: the message is the HTTP status text, or
    ///   `"request failed"` when that is empty.
    public static func normalize(
        body: TemperaJSON?,
        statusText: String = ""
    ) -> TemperaNormalizedError {
        if let error = body?["error"] {
            switch error {
            case .object:
                // `error.status` wins over `error.code` only when it is a
                // string: the canonical envelope puts the enum in `status` and
                // the integer HTTP code in `code`.
                let code = error["status"]?.stringValue ?? error["code"]?.stringValue
                return TemperaNormalizedError(
                    code: code,
                    message: error["message"]?.stringValue ?? statusText,
                    reason: errorInfoReason(error),
                    requestId: error["requestId"]?.stringValue
                        ?? error["request_id"]?.stringValue
                )
            case let .string(text):
                if let message = body?["message"]?.stringValue {
                    return TemperaNormalizedError(
                        code: text, message: message, reason: nil, requestId: nil)
                }
                return TemperaNormalizedError(
                    code: nil, message: text, reason: nil, requestId: nil)
            default:
                break
            }
        }
        return TemperaNormalizedError(
            code: nil,
            message: statusText.isEmpty ? "request failed" : statusText,
            reason: nil,
            requestId: nil
        )
    }

    /// Build one error from a failed HTTP response. `requestId` falls back to
    /// the `x-request-id` response header.
    public static func from(
        status: Int,
        statusText: String = "",
        headers: [TemperaKeyValue] = [],
        body: TemperaJSON? = nil,
        product: String? = nil,
        operation: String? = nil
    ) -> TemperaApiError {
        let normalized = normalize(body: body, statusText: statusText)
        let headerRequestId = headers.first { $0.key.lowercased() == "x-request-id" }?.value
        let label = [product, operation].compactMap { $0 }.joined(separator: ".")
        return TemperaApiError(
            status: status,
            code: normalized.code,
            message: "Tempera \(label.isEmpty ? "request" : label) failed "
                + "(\(status)): \(normalized.message)",
            reason: normalized.reason,
            requestId: normalized.requestId ?? headerRequestId,
            product: product,
            operation: operation,
            body: body,
            statusText: statusText
        )
    }

    /// Re-label a context-free error (one a transport raised) with the product
    /// and operation that made the request.
    public func withContext(product: String?, operation: String?) -> TemperaApiError {
        guard self.product == nil, self.operation == nil else { return self }
        let headers = requestId.map { [TemperaKeyValue(key: "x-request-id", value: $0)] } ?? []
        return TemperaApiError.from(
            status: status,
            statusText: statusText,
            headers: headers,
            body: body,
            product: product,
            operation: operation
        )
    }
}
