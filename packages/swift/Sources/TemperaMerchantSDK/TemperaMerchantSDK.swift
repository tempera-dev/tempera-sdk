import Foundation

public enum MerchantCategory: String, Codable, Sendable {
    case physicalGoods = "physical_goods"
    case offlineServices = "offline_services"
}

public enum MerchantNextAction: String, Codable, Sendable {
    case startOnboarding = "start_onboarding"
    case continueOnboarding = "continue_onboarding"
    case refreshRequirements = "refresh_requirements"
    case waitForProvider = "wait_for_provider"
    case contactSupport = "contact_support"
    case ready
}

public struct CreateMerchantRequest: Codable, Sendable {
    public let tenantID: String
    public let country: String
    public let currency: String
    public let category: MerchantCategory

    public init(
        tenantID: String,
        country: String = "US",
        currency: String = "usd",
        category: MerchantCategory
    ) {
        self.tenantID = tenantID
        self.country = country
        self.currency = currency
        self.category = category
    }

    enum CodingKeys: String, CodingKey {
        case tenantID = "tenant_id"
        case country
        case currency
        case category
    }
}

public struct MerchantTenantRequest: Codable, Sendable {
    public let tenantID: String

    public init(tenantID: String) {
        self.tenantID = tenantID
    }

    enum CodingKeys: String, CodingKey {
        case tenantID = "tenant_id"
    }
}

public struct Merchant: Codable, Sendable, Equatable {
    public let id: UUID
    public let tenantID: String
    public let country: String
    public let currency: String
    public let category: MerchantCategory
    public let workspaceReady: Bool
    public let paymentsEnabled: Bool
    public let payoutsEnabled: Bool
    public let actionRequired: Bool
    public let requirementsCurrent: Bool
    public let currentlyDue: [String]
    public let pastDue: [String]
    public let pendingVerification: [String]
    public let disabledReason: String?
    public let nextAction: MerchantNextAction
    public let providerObservedAt: Int64?

    enum CodingKeys: String, CodingKey {
        case id
        case tenantID = "tenant_id"
        case country
        case currency
        case category
        case workspaceReady = "workspace_ready"
        case paymentsEnabled = "payments_enabled"
        case payoutsEnabled = "payouts_enabled"
        case actionRequired = "action_required"
        case requirementsCurrent = "requirements_current"
        case currentlyDue = "currently_due"
        case pastDue = "past_due"
        case pendingVerification = "pending_verification"
        case disabledReason = "disabled_reason"
        case nextAction = "next_action"
        case providerObservedAt = "provider_observed_at"
    }

    public func isReady(now: Date = Date()) -> Bool {
        guard
            nextAction == .ready,
            requirementsCurrent,
            paymentsEnabled,
            payoutsEnabled,
            let observed = providerObservedAt
        else {
            return false
        }

        let age = now.timeIntervalSince1970 - TimeInterval(observed)
        return age >= 0 && age < 300
    }
}

public struct MerchantWorkspace: Codable, Sendable, Equatable {
    public let tenantID: String
    public let merchant: Merchant?

    enum CodingKeys: String, CodingKey {
        case tenantID = "tenant_id"
        case merchant
    }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        tenantID = try values.decode(String.self, forKey: .tenantID)
        guard values.contains(.merchant) else {
            throw DecodingError.keyNotFound(
                CodingKeys.merchant,
                .init(
                    codingPath: decoder.codingPath,
                    debugDescription:
                        "The workspace response must include merchant, even when null."))
        }
        merchant = try values.decodeIfPresent(Merchant.self, forKey: .merchant)
    }

    public func encode(to encoder: any Encoder) throws {
        var values = encoder.container(keyedBy: CodingKeys.self)
        try values.encode(tenantID, forKey: .tenantID)
        try values.encode(merchant, forKey: .merchant)
    }
}

public struct MerchantOnboardingLink: Codable, Sendable, Equatable {
    public let merchantID: UUID
    public let url: URL
    public let expiresAt: Int64

    enum CodingKeys: String, CodingKey {
        case merchantID = "merchant_id"
        case url
        case expiresAt = "expires_at"
    }
}

public enum MerchantClientError: Error, LocalizedError, Sendable, Equatable {
    case invalidOrigin
    case invalidRequest(String)
    case cancelled
    case responseTooLarge
    case invalidResponse(String)
    case server(statusCode: Int, code: String?, message: String?)

    public var errorDescription: String? {
        switch self {
        case .invalidOrigin:
            return "The Payments service address is invalid."
        case .invalidRequest(let message), .invalidResponse(let message):
            return message
        case .cancelled:
            return "The request was cancelled."
        case .responseTooLarge:
            return "The service response was too large to process safely."
        case .server(let statusCode, _, let message):
            return message ?? "The Payments service returned HTTP \(statusCode)."
        }
    }
}

/// The client holds immutable configuration and Foundation's thread-safe session.
/// The delegate has no mutable request state, so sharing this client across actors
/// does not share mutable application state.
public final class MerchantClient: Sendable {
    public typealias BearerTokenProvider = @Sendable () async throws -> String

    private static let maxResponseBytes = 256 * 1024
    private static let requestTimeout: TimeInterval = 15
    private static let resourceTimeout: TimeInterval = 30

    private let origin: URL
    private let tokenProvider: BearerTokenProvider
    private let redirectDelegate: RedirectDenyingDelegate
    private let session: URLSession

    public convenience init(origin: URL, bearerToken: @escaping BearerTokenProvider) throws {
        try self.init(origin: origin, bearerToken: bearerToken, protocolClasses: nil)
    }

    init(
        origin: URL,
        bearerToken: @escaping BearerTokenProvider,
        protocolClasses: [AnyClass]?
    ) throws {
        guard Self.isValidOrigin(origin) else {
            throw MerchantClientError.invalidOrigin
        }

        self.origin = origin
        self.tokenProvider = bearerToken
        self.redirectDelegate = RedirectDenyingDelegate()

        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = protocolClasses
        configuration.urlCache = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.httpShouldSetCookies = false
        configuration.timeoutIntervalForRequest = Self.requestTimeout
        configuration.timeoutIntervalForResource = Self.resourceTimeout
        self.session = URLSession(
            configuration: configuration,
            delegate: redirectDelegate,
            delegateQueue: nil
        )
    }

    deinit {
        session.invalidateAndCancel()
    }

    public func create(
        _ request: CreateMerchantRequest,
        idempotencyKey: String
    ) async throws -> Merchant {
        try validateTenant(request.tenantID)
        guard request.country == "US", request.currency == "usd" else {
            throw MerchantClientError.invalidRequest(
                "Merchant onboarding supports US and usd only."
            )
        }

        return try await send(
            // tempera-transport: temperaPayments.createMerchant POST /v1/merchants
            path: "/v1/merchants",
            method: "POST",
            query: [],
            body: request,
            idempotencyKey: idempotencyKey,
            expectedMerchantID: nil,
            expectedTenantID: request.tenantID
        )
    }

    public func workspaceMerchant(tenantID: String) async throws -> Merchant {
        try validateTenant(tenantID)
        return try await send(
            // tempera-transport: temperaPayments.getWorkspaceMerchant GET /v1/merchants
            path: "/v1/merchants",
            method: "GET",
            query: [URLQueryItem(name: "tenant_id", value: tenantID)],
            body: Optional<MerchantTenantRequest>.none,
            idempotencyKey: nil,
            expectedMerchantID: nil,
            expectedTenantID: tenantID
        )
    }

    public func workspace() async throws -> MerchantWorkspace {
        let workspace: MerchantWorkspace = try await sendRaw(
            // tempera-transport: temperaPayments.getMerchantWorkspace GET /v1/merchants/workspace
            path: "/v1/merchants/workspace",
            method: "GET",
            query: [],
            body: Optional<MerchantTenantRequest>.none,
            idempotencyKey: nil
        )
        try validateTenant(workspace.tenantID)
        if let merchant = workspace.merchant {
            guard merchant.tenantID == workspace.tenantID, merchant.country == "US",
                merchant.currency == "usd"
            else {
                throw MerchantClientError.invalidResponse(
                    "The merchant response did not match the authenticated workspace.")
            }
        }
        return workspace
    }

    public func merchant(id: UUID, tenantID: String) async throws -> Merchant {
        try validateTenant(tenantID)
        let merchantID = id.uuidString.lowercased()
        return try await send(
            // tempera-transport: temperaPayments.getMerchant GET /v1/merchants/{merchant_id}
            path: "/v1/merchants/\(merchantID)",
            method: "GET",
            query: [URLQueryItem(name: "tenant_id", value: tenantID)],
            body: Optional<MerchantTenantRequest>.none,
            idempotencyKey: nil,
            expectedMerchantID: id,
            expectedTenantID: tenantID
        )
    }

    public func refresh(id: UUID, tenantID: String) async throws -> Merchant {
        try validateTenant(tenantID)
        let merchantID = id.uuidString.lowercased()
        return try await send(
            // tempera-transport: temperaPayments.refreshMerchantEligibility POST /v1/merchants/{merchant_id}/refresh
            path: "/v1/merchants/\(merchantID)/refresh",
            method: "POST",
            query: [],
            body: MerchantTenantRequest(tenantID: tenantID),
            idempotencyKey: nil,
            expectedMerchantID: id,
            expectedTenantID: tenantID
        )
    }

    public func onboarding(
        id: UUID,
        tenantID: String,
        idempotencyKey: String
    ) async throws -> MerchantOnboardingLink {
        try validateTenant(tenantID)
        let merchantID = id.uuidString.lowercased()
        let link: MerchantOnboardingLink = try await sendRaw(
            // tempera-transport: temperaPayments.createMerchantOnboardingLink POST /v1/merchants/{merchant_id}/onboarding
            path: "/v1/merchants/\(merchantID)/onboarding",
            method: "POST",
            query: [],
            body: MerchantTenantRequest(tenantID: tenantID),
            idempotencyKey: idempotencyKey
        )

        guard link.merchantID == id, Self.isValidOnboardingURL(link.url) else {
            throw MerchantClientError.invalidResponse(
                "The onboarding link could not be verified."
            )
        }
        guard link.expiresAt > Int64(Date().timeIntervalSince1970) else {
            throw MerchantClientError.invalidResponse(
                "The onboarding link has expired. Request a new link."
            )
        }
        return link
    }

    private func send<B: Encodable>(
        path: String,
        method: String,
        query: [URLQueryItem],
        body: B?,
        idempotencyKey: String?,
        expectedMerchantID: UUID?,
        expectedTenantID: String
    ) async throws -> Merchant {
        let merchant: Merchant = try await sendRaw(
            path: path,
            method: method,
            query: query,
            body: body,
            idempotencyKey: idempotencyKey
        )

        guard
            merchant.tenantID == expectedTenantID,
            expectedMerchantID == nil || merchant.id == expectedMerchantID,
            merchant.country == "US",
            merchant.currency == "usd"
        else {
            throw MerchantClientError.invalidResponse(
                "The merchant response did not match the requested workspace."
            )
        }
        return merchant
    }

    private func sendRaw<T: Decodable, B: Encodable>(
        path: String,
        method: String,
        query: [URLQueryItem],
        body: B?,
        idempotencyKey: String?
    ) async throws -> T {
        if Task.isCancelled {
            throw MerchantClientError.cancelled
        }

        var components = URLComponents(url: origin, resolvingAgainstBaseURL: false)!
        components.path = path
        components.queryItems = query.isEmpty ? nil : query
        guard let url = components.url else {
            throw MerchantClientError.invalidOrigin
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = Self.requestTimeout
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let idempotencyKey {
            try validateIdempotencyKey(idempotencyKey)
            request.setValue(idempotencyKey, forHTTPHeaderField: "Idempotency-Key")
        }
        if let body {
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
            request.httpBody = try encoder.encode(body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let token = try await tokenProvider()
        guard !token.isEmpty, !token.contains(where: { $0.isWhitespace || $0.isNewline }) else {
            throw MerchantClientError.invalidRequest(
                "A valid human OAuth bearer token is required."
            )
        }
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        do {
            let (bytes, response) = try await session.bytes(for: request)
            guard let http = response as? HTTPURLResponse else {
                throw MerchantClientError.invalidResponse(
                    "The Payments service returned an invalid response."
                )
            }
            if let contentLength = http.value(forHTTPHeaderField: "Content-Length").flatMap(
                Int.init),
                contentLength > Self.maxResponseBytes
            {
                bytes.task.cancel()
                throw MerchantClientError.responseTooLarge
            }

            var data = Data()
            data.reserveCapacity(
                min(
                    http.expectedContentLength > 0 ? Int(http.expectedContentLength) : 0,
                    Self.maxResponseBytes
                )
            )
            for try await byte in bytes {
                try Task.checkCancellation()
                if data.count >= Self.maxResponseBytes {
                    bytes.task.cancel()
                    throw MerchantClientError.responseTooLarge
                }
                data.append(byte)
            }

            guard (200...299).contains(http.statusCode) else {
                let error = decodeServerError(data)
                throw MerchantClientError.server(
                    statusCode: http.statusCode,
                    code: error.code,
                    message: error.message
                )
            }

            do {
                return try JSONDecoder().decode(T.self, from: data)
            } catch {
                throw MerchantClientError.invalidResponse(
                    "The Payments service returned an invalid response."
                )
            }
        } catch is CancellationError {
            throw MerchantClientError.cancelled
        } catch let error as URLError where error.code == .cancelled || Task.isCancelled {
            throw MerchantClientError.cancelled
        } catch let error as MerchantClientError {
            throw error
        } catch {
            throw MerchantClientError.invalidResponse(
                "The Payments service could not be reached."
            )
        }
    }

    private static func isValidOrigin(_ url: URL) -> Bool {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            return false
        }
        return components.scheme == "https"
            && components.host != nil
            && components.user == nil
            && components.password == nil
            && components.query == nil
            && components.fragment == nil
            && (components.path.isEmpty || components.path == "/")
            && (components.port == nil || components.port == 443)
    }

    private static func isValidOnboardingURL(_ url: URL) -> Bool {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            return false
        }
        return components.scheme == "https"
            && components.host == "connect.stripe.com"
            && (components.port == nil || components.port == 443)
            && components.user == nil
            && components.password == nil
            && components.fragment == nil
    }
}

final class RedirectDenyingDelegate: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        willPerformHTTPRedirection response: HTTPURLResponse,
        newRequest request: URLRequest,
        completionHandler: @escaping (URLRequest?) -> Void
    ) {
        completionHandler(nil)
    }
}

private func validateTenant(_ tenant: String) throws {
    guard
        !tenant.isEmpty,
        tenant.utf8.count <= 128,
        tenant == tenant.trimmingCharacters(in: .whitespacesAndNewlines),
        tenant.rangeOfCharacter(from: .controlCharacters) == nil
    else {
        throw MerchantClientError.invalidRequest("A valid workspace is required.")
    }
}

private func validateIdempotencyKey(_ key: String) throws {
    guard
        !key.isEmpty,
        key.count <= 255,
        key.unicodeScalars.allSatisfy({ (33...126).contains(Int($0.value)) })
    else {
        throw MerchantClientError.invalidRequest(
            "An Idempotency-Key of 1–255 visible ASCII characters is required."
        )
    }
}

private struct ServerError: Decodable {
    struct Detail: Decodable {
        let code: String?
        let message: String?
    }

    let error: Detail?
}

private func decodeServerError(_ data: Data) -> (code: String?, message: String?) {
    let detail = (try? JSONDecoder().decode(ServerError.self, from: data))?.error
    return (detail?.code, detail?.message)
}
