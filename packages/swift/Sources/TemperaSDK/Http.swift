// The transport seam: one request value, one response value, one protocol.
//
// Everything above this file (dispatch, auth, MCP) builds a
// `TemperaHTTPRequest` and reads a `TemperaHTTPResponse`, so tests drive the
// whole client through a stub without a socket, exactly as the TypeScript
// package injects `fetch` and the Python package injects `transport`.

import Foundation

#if canImport(FoundationNetworking)
    import FoundationNetworking
#endif

/// One outbound HTTP request.
public struct TemperaHTTPRequest: Sendable, Equatable {
    /// HTTP method (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).
    public var method: String
    /// Absolute URL, including any query string.
    public var url: String
    /// Request headers, lowercase-named, in emission order.
    public var headers: [TemperaKeyValue]
    /// Request body bytes, when the request carries one.
    public var body: Data?
    /// How long to wait for the complete response.
    public var timeout: TimeInterval

    /// Create one request.
    public init(
        method: String,
        url: String,
        headers: [TemperaKeyValue] = [],
        body: Data? = nil,
        timeout: TimeInterval = TemperaClientConfiguration.defaultTimeout
    ) {
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body
        self.timeout = timeout
    }

    /// One header's value, matched case-insensitively.
    public func header(_ name: String) -> String? {
        let wanted = name.lowercased()
        return headers.first { $0.key.lowercased() == wanted }?.value
    }
}

/// One inbound HTTP response.
public struct TemperaHTTPResponse: Sendable, Equatable {
    /// HTTP status code.
    public var status: Int
    /// HTTP status text (reason phrase).
    public var statusText: String
    /// Response headers.
    public var headers: [TemperaKeyValue]
    /// Response body bytes.
    public var body: Data

    /// Create one response.
    public init(
        status: Int,
        statusText: String = "",
        headers: [TemperaKeyValue] = [],
        body: Data = Data()
    ) {
        self.status = status
        self.statusText = statusText.isEmpty ? TemperaHTTPResponse.reasonPhrase(status) : statusText
        self.headers = headers
        self.body = body
    }

    /// One header's value, matched case-insensitively.
    public func header(_ name: String) -> String? {
        let wanted = name.lowercased()
        return headers.first { $0.key.lowercased() == wanted }?.value
    }

    /// Whether the status is 2xx.
    public var isSuccess: Bool { (200..<300).contains(status) }

    /// The body parsed as JSON, or `nil` when it is empty or not JSON.
    public var json: TemperaJSON? {
        body.isEmpty ? nil : TemperaJSON.parse(body)
    }

    /// The standard reason phrase for a status code.
    ///
    /// `URLSession` does not surface the server's reason phrase, and the
    /// localized fallback is lowercase; the uniform error contract wants the
    /// same text the TypeScript and Python packages report.
    public static func reasonPhrase(_ status: Int) -> String {
        switch status {
        case 200: return "OK"
        case 201: return "Created"
        case 202: return "Accepted"
        case 204: return "No Content"
        case 301: return "Moved Permanently"
        case 302: return "Found"
        case 304: return "Not Modified"
        case 400: return "Bad Request"
        case 401: return "Unauthorized"
        case 403: return "Forbidden"
        case 404: return "Not Found"
        case 405: return "Method Not Allowed"
        case 408: return "Request Timeout"
        case 409: return "Conflict"
        case 410: return "Gone"
        case 413: return "Payload Too Large"
        case 415: return "Unsupported Media Type"
        case 422: return "Unprocessable Entity"
        case 429: return "Too Many Requests"
        case 500: return "Internal Server Error"
        case 501: return "Not Implemented"
        case 502: return "Bad Gateway"
        case 503: return "Service Unavailable"
        case 504: return "Gateway Timeout"
        default: return HTTPURLResponse.localizedString(forStatusCode: status)
        }
    }
}

/// Sends one request and returns one response. Non-2xx statuses are responses,
/// not errors: only a failure to obtain a response throws.
public protocol TemperaTransport: Sendable {
    /// Send one request.
    func send(_ request: TemperaHTTPRequest) async throws -> TemperaHTTPResponse
}

/// The default transport: `URLSession` with async/await and a per-request
/// timeout.
public struct TemperaURLSessionTransport: TemperaTransport {
    private let session: URLSession

    /// Create a transport over one session (`URLSession.shared` by default).
    public init(session: URLSession = .shared) {
        self.session = session
    }

    public func send(_ request: TemperaHTTPRequest) async throws -> TemperaHTTPResponse {
        guard let url = URL(string: request.url) else {
            throw TemperaSdkError("invalid request URL: \(request.url)")
        }
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = request.method
        urlRequest.httpBody = request.body
        urlRequest.timeoutInterval = request.timeout
        for header in request.headers {
            urlRequest.setValue(header.value, forHTTPHeaderField: header.key)
        }
        do {
            let (data, response) = try await session.data(for: urlRequest)
            guard let http = response as? HTTPURLResponse else {
                throw TemperaTransportError("response was not HTTP")
            }
            let headers: [TemperaKeyValue] = http.allHeaderFields.compactMap { key, value in
                guard let name = key as? String else { return nil }
                return TemperaKeyValue(key: name.lowercased(), value: "\(value)")
            }
            return TemperaHTTPResponse(
                status: http.statusCode,
                statusText: TemperaHTTPResponse.reasonPhrase(http.statusCode),
                headers: headers,
                body: data
            )
        } catch let error as TemperaFailure {
            throw error
        } catch {
            // A URLSession failure means no HTTP response existed, which is
            // what the retry policy treats as a transient connection failure.
            throw TemperaTransportError(error.localizedDescription)
        }
    }
}
