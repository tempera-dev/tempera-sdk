import Foundation

public enum OrdersCommerceError: Error, LocalizedError, Sendable, Equatable {
    case invalidConfiguration
    case invalidRequest
    case cancelled
    case unavailable
    case responseTooLarge
    case invalidResponse
    case authorizationRequired
    case notFound
    case server(Int)

    public var errorDescription: String? {
        switch self {
        case .invalidConfiguration: "The Orders connection needs a valid service and workspace."
        case .invalidRequest: "The requested order or page is invalid."
        case .cancelled: "The request was cancelled."
        case .unavailable: "Orders could not be reached. Try loading again."
        case .responseTooLarge, .invalidResponse:
            "The Orders response could not be verified. Try loading again."
        case .authorizationRequired: "Reconnect Orders to view this workspace."
        case .notFound: "This record was not found in the selected workspace."
        case .server: "Orders is temporarily unavailable. Try loading again."
        }
    }
}

/// Reads declared commerce records. These records do not establish payment or payout status.
public final class OrdersCommerceClient: Sendable {
    private let origin: URL
    private let scope: OrdersWorkspaceScope
    private let merchantID: UUID
    private let bearerToken: MerchantClient.BearerTokenProvider
    private let session: URLSession
    private let delegate: RedirectDenyingDelegate
    private static let maximumBytes = 256 * 1024

    public convenience init(
        origin: URL, scope: OrdersWorkspaceScope, merchantID: UUID,
        bearerToken: @escaping MerchantClient.BearerTokenProvider
    ) throws {
        try self.init(
            origin: origin, scope: scope, merchantID: merchantID,
            bearerToken: bearerToken, protocolClasses: nil)
    }

    init(
        origin: URL, scope: OrdersWorkspaceScope, merchantID: UUID,
        bearerToken: @escaping MerchantClient.BearerTokenProvider,
        protocolClasses: [AnyClass]?
    ) throws {
        guard let parts = URLComponents(url: origin, resolvingAgainstBaseURL: false),
            parts.scheme == "https", let host = parts.host, !host.isEmpty,
            parts.user == nil, parts.password == nil, parts.query == nil,
            parts.fragment == nil, parts.path.isEmpty || parts.path == "/",
            parts.port == nil || parts.port == 443
        else {
            throw OrdersCommerceError.invalidConfiguration
        }
        self.origin = origin
        self.scope = scope
        self.merchantID = merchantID
        self.bearerToken = bearerToken
        self.delegate = RedirectDenyingDelegate()
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = protocolClasses
        configuration.urlCache = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.httpShouldSetCookies = false
        configuration.timeoutIntervalForRequest = 15
        configuration.timeoutIntervalForResource = 30
        self.session = URLSession(
            configuration: configuration, delegate: delegate, delegateQueue: nil)
    }

    deinit { session.invalidateAndCancel() }

    public func offers(pageToken: String? = nil, pageSize: Int = 50) async throws -> CatalogOfferPage {
        let organization = segment(scope.organizationID)
        let project = segment(scope.projectID)
        let environment = segment(scope.environment.rawValue)
        let site = segment(scope.siteID)
        let page: CatalogOfferPage = try await read(
            path:
            // tempera-transport: temperaDropshipping.listCatalogOffers GET /v1/organizations/{organization}/projects/{project}/environments/{environment}/sites/{site}/catalog/offers
                "/v1/organizations/\(organization)/projects/\(project)/environments/\(environment)/sites/\(site)/catalog/offers",
            query: try pageQuery(pageToken: pageToken, pageSize: pageSize))
        guard page.items.count <= pageSize,
            page.items.allSatisfy({ $0.scope == scope && $0.merchantID == merchantID }),
            Set(page.items.map(\.id)).count == page.items.count
        else { throw OrdersCommerceError.invalidResponse }
        return page
    }

    public func offer(id: String) async throws -> CatalogOffer {
        try resourceID(id)
        let organization = segment(scope.organizationID)
        let project = segment(scope.projectID)
        let environment = segment(scope.environment.rawValue)
        let site = segment(scope.siteID)
        let offerID = segment(id)
        let offer: CatalogOffer = try await read(
            path:
            // tempera-transport: temperaDropshipping.getCatalogOffer GET /v1/organizations/{organization}/projects/{project}/environments/{environment}/sites/{site}/catalog/offers/{offerId}
                "/v1/organizations/\(organization)/projects/\(project)/environments/\(environment)/sites/\(site)/catalog/offers/\(offerID)",
            query: [])
        guard offer.scope == scope, offer.merchantID == merchantID, offer.id == id else {
            throw OrdersCommerceError.invalidResponse
        }
        return offer
    }

    public func saleOrders(pageToken: String? = nil, pageSize: Int = 50) async throws -> SaleOrderPage {
        let organization = segment(scope.organizationID)
        let project = segment(scope.projectID)
        let environment = segment(scope.environment.rawValue)
        let site = segment(scope.siteID)
        let page: SaleOrderPage = try await read(
            path:
            // tempera-transport: temperaDropshipping.listSaleOrders GET /v1/organizations/{organization}/projects/{project}/environments/{environment}/sites/{site}/sale-orders
                "/v1/organizations/\(organization)/projects/\(project)/environments/\(environment)/sites/\(site)/sale-orders",
            query: try pageQuery(pageToken: pageToken, pageSize: pageSize))
        guard page.items.count <= pageSize,
            page.items.allSatisfy({ $0.scope == scope && $0.merchantID == merchantID }),
            Set(page.items.map(\.id)).count == page.items.count
        else { throw OrdersCommerceError.invalidResponse }
        return page
    }

    public func saleOrder(id: String) async throws -> SaleOrder {
        try resourceID(id)
        let organization = segment(scope.organizationID)
        let project = segment(scope.projectID)
        let environment = segment(scope.environment.rawValue)
        let site = segment(scope.siteID)
        let orderID = segment(id)
        let order: SaleOrder = try await read(
            path:
            // tempera-transport: temperaDropshipping.getSaleOrder GET /v1/organizations/{organization}/projects/{project}/environments/{environment}/sites/{site}/sale-orders/{orderId}
                "/v1/organizations/\(organization)/projects/\(project)/environments/\(environment)/sites/\(site)/sale-orders/\(orderID)",
            query: [])
        guard order.scope == scope, order.merchantID == merchantID, order.id == id else {
            throw OrdersCommerceError.invalidResponse
        }
        return order
    }

    private func pageQuery(pageToken: String?, pageSize: Int) throws -> [URLQueryItem] {
        guard (1...100).contains(pageSize) else { throw OrdersCommerceError.invalidRequest }
        var query = [URLQueryItem(name: "pageSize", value: String(pageSize))]
        if let pageToken {
            try resourceID(pageToken)
            query.append(URLQueryItem(name: "pageToken", value: pageToken))
        }
        return query
    }

    private func read<T: Decodable>(path: String, query: [URLQueryItem]) async throws -> T {
        do {
            try Task.checkCancellation()
            guard var parts = URLComponents(url: origin, resolvingAgainstBaseURL: false) else {
                throw OrdersCommerceError.invalidConfiguration
            }
            parts.percentEncodedPath = path
            parts.queryItems = query.isEmpty ? nil : query
            guard let url = parts.url else { throw OrdersCommerceError.invalidRequest }
            let token = try await bearerToken()
            try Task.checkCancellation()
            guard !token.isEmpty, token.utf8.count <= 4096,
                token.unicodeScalars.allSatisfy({ (33...126).contains(Int($0.value)) })
            else {
                throw OrdersCommerceError.authorizationRequired
            }
            var request = URLRequest(url: url)
            request.httpMethod = "GET"
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            request.setValue("application/json", forHTTPHeaderField: "Accept")
            request.timeoutInterval = 15
            let (bytes, response) = try await session.bytes(for: request)
            defer { bytes.task.cancel() }
            guard let http = response as? HTTPURLResponse else {
                throw OrdersCommerceError.invalidResponse
            }
            if http.expectedContentLength > Self.maximumBytes {
                throw OrdersCommerceError.responseTooLarge
            }
            if http.statusCode == 401 || http.statusCode == 403 {
                throw OrdersCommerceError.authorizationRequired
            }
            if http.statusCode == 404 { throw OrdersCommerceError.notFound }
            guard http.statusCode == 200 else { throw OrdersCommerceError.server(http.statusCode) }
            guard
                http.value(forHTTPHeaderField: "Content-Type")?.split(separator: ";").first?
                    .lowercased()
                    .trimmingCharacters(in: .whitespaces) == "application/json"
            else {
                throw OrdersCommerceError.invalidResponse
            }
            var data = Data()
            for try await byte in bytes {
                try Task.checkCancellation()
                guard data.count < Self.maximumBytes else {
                    throw OrdersCommerceError.responseTooLarge
                }
                data.append(byte)
            }
            do { return try JSONDecoder().decode(T.self, from: data) } catch {
                throw OrdersCommerceError.invalidResponse
            }
        } catch is CancellationError { throw OrdersCommerceError.cancelled } catch let error
            as URLError where error.code == .cancelled || Task.isCancelled
        { throw OrdersCommerceError.cancelled } catch let error as OrdersCommerceError {
            throw error
        } catch { throw OrdersCommerceError.unavailable }
    }

    private func segment(_ value: String) -> String {
        value.addingPercentEncoding(
            withAllowedCharacters: CharacterSet(
                charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"))!
    }

    private func resourceID(_ value: String) throws {
        guard
            value.range(of: #"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"#, options: .regularExpression)
                == value.startIndex..<value.endIndex
        else {
            throw OrdersCommerceError.invalidRequest
        }
    }
}
