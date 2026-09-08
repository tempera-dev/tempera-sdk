import Foundation

/// The four-part Orders workspace identity. It is carried by every declared
/// commerce record and is never inferred from a client URL.
public struct OrdersWorkspaceScope: Codable, Equatable, Hashable, Sendable {
    public enum Environment: String, Codable, Sendable {
        case development, test, staging, production
    }

    public let organizationID: String
    public let projectID: String
    public let environment: Environment
    public let siteID: String

    public init(organizationID: String, projectID: String, environment: Environment, siteID: String)
        throws
    {
        guard Self.validateIdentifier(organizationID), Self.validateIdentifier(projectID),
            Self.validateIdentifier(siteID)
        else {
            throw CommerceModelError.invalidScope
        }
        self.organizationID = organizationID
        self.projectID = projectID
        self.environment = environment
        self.siteID = siteID
    }

    enum CodingKeys: String, CodingKey, CaseIterable {
        case organizationID = "organization_id"
        case projectID = "project_id"
        case environment
        case siteID = "site_id"
    }

    public init(from decoder: any Decoder) throws {
        try CommerceCoding.exactKeys(
            decoder, ["organization_id", "project_id", "environment", "site_id"])
        let values = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(
            organizationID: values.decode(String.self, forKey: .organizationID),
            projectID: values.decode(String.self, forKey: .projectID),
            environment: values.decode(Environment.self, forKey: .environment),
            siteID: values.decode(String.self, forKey: .siteID)
        )
    }

    private static func validateIdentifier(_ value: String) -> Bool {
        guard !value.isEmpty, value.utf8.count <= 160 else { return false }
        guard
            let range = value.range(
                of: "^[A-Za-z0-9][A-Za-z0-9_.:/@-]*$", options: .regularExpression)
        else { return false }
        return range == value.startIndex..<value.endIndex
    }
}

public enum CommerceModelError: Error, LocalizedError, Equatable, Sendable {
    case invalidScope
    case invalidResource
    case invalidMerchantID
    case invalidPhotoURL
    case invalidAmount

    public var errorDescription: String? {
        switch self {
        case .invalidScope: return "The Orders workspace scope is invalid."
        case .invalidResource: return "The Orders resource identifier is invalid."
        case .invalidMerchantID: return "The merchant identifier is invalid."
        case .invalidPhotoURL: return "The offer photo URL is invalid."
        case .invalidAmount: return "The sale order amount is invalid."
        }
    }
}

private enum CommerceCoding {
    struct Key: CodingKey {
        let stringValue: String
        init?(stringValue: String) { self.stringValue = stringValue }
        let intValue: Int? = nil
        init?(intValue: Int) { return nil }
    }

    static func exactKeys(_ decoder: any Decoder, _ expected: Set<String>) throws {
        let actual = try decoder.container(keyedBy: Key.self).allKeys.map(\.stringValue)
        guard Set(actual) == expected else { throw CommerceModelError.invalidResource }
    }

    static func merchantID(_ value: String) throws -> UUID {
        let bytes = Array(value.utf8)
        guard let uuid = UUID(uuidString: value), bytes.count == 36,
            bytes[14] == 49 || bytes[14] == 50 || bytes[14] == 51 || bytes[14] == 52
                || bytes[14] == 53 || bytes[14] == 54 || bytes[14] == 55 || bytes[14] == 56
        else {
            throw CommerceModelError.invalidMerchantID
        }
        guard [56, 57, 65, 66, 97, 98].contains(bytes[19]) else {
            throw CommerceModelError.invalidMerchantID
        }
        return uuid
    }

    static func resource(_ value: String) throws -> String {
        guard !value.isEmpty, value.utf8.count <= 128,
            let range = value.range(
                of: "^[A-Za-z0-9][A-Za-z0-9_.-]*$", options: .regularExpression),
            range == value.startIndex..<value.endIndex
        else {
            throw CommerceModelError.invalidResource
        }
        return value
    }

    static func date(_ value: String) throws -> Date {
        guard
            value.range(
                of:
                    #"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,9})?(Z|[+-][0-9]{2}:[0-9]{2})\z"#,
                options: .regularExpression) != nil
        else {
            throw CommerceModelError.invalidResource
        }
        let bytes = Array(value.utf8)
        func number(_ start: Int, _ end: Int) -> Int {
            Int(String(decoding: bytes[start..<end], as: UTF8.self))!
        }
        let year = number(0, 4)
        let month = number(5, 7)
        let day = number(8, 10)
        let hour = number(11, 13)
        let minute = number(14, 16)
        let second = number(17, 19)
        guard year > 0, (1...12).contains(month), (1...31).contains(day),
            hour < 24, minute < 60, second < 60
        else { throw CommerceModelError.invalidResource }
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        let components = DateComponents(
            year: year, month: month, day: day, hour: hour, minute: minute, second: second)
        guard let date = calendar.date(from: components),
            calendar.component(.year, from: date) == year,
            calendar.component(.month, from: date) == month,
            calendar.component(.day, from: date) == day
        else { throw CommerceModelError.invalidResource }
        let zoneStart = bytes.last == 90 ? bytes.count - 1 : bytes.count - 6
        var offset = 0
        if bytes.last != 90 {
            let zoneHour = number(zoneStart + 1, zoneStart + 3)
            let zoneMinute = number(zoneStart + 4, zoneStart + 6)
            guard zoneHour < 24, zoneMinute < 60 else { throw CommerceModelError.invalidResource }
            offset = (zoneHour * 3600 + zoneMinute * 60) * (bytes[zoneStart] == 45 ? -1 : 1)
        }
        let fraction =
            zoneStart == 19
            ? 0 : Double("0" + String(decoding: bytes[19..<zoneStart], as: UTF8.self))!
        return date.addingTimeInterval(fraction - Double(offset))
    }

    static func photo(_ value: String?) throws -> URL? {
        guard let value else { return nil }
        guard let url = URL(string: value),
            let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
            value.hasPrefix("https://"), !value.contains(where: { $0.isWhitespace }),
            components.scheme == "https", components.host?.isEmpty == false, components.user == nil,
            components.password == nil, components.fragment == nil, value.count <= 2048
        else {
            throw CommerceModelError.invalidPhotoURL
        }
        return url
    }
}

public struct CatalogOffer: Decodable, Equatable, Sendable {
    public let id: String
    public let revision: Int
    public let scope: OrdersWorkspaceScope
    public let merchantID: UUID
    public let productClassification: MerchantCategory
    public let name: String
    public let description: String
    public let photoURL: URL?
    public let currency: String
    public let unitAmountMinor: Int64
    public let createdAt: Date
    public let expiresAt: Date?

    enum CodingKeys: String, CodingKey, CaseIterable {
        case id, revision, scope
        case merchantID = "merchant_id"
        case productClassification = "product_classification"
        case name, description
        case photoURL = "photo_url"
        case currency
        case unitAmountMinor = "unit_amount_minor"
        case createdAt = "created_at"
        case expiresAt = "expires_at"
    }

    public init(from decoder: any Decoder) throws {
        try CommerceCoding.exactKeys(
            decoder,
            [
                "id", "revision", "scope", "merchant_id", "product_classification", "name",
                "description", "photo_url", "currency", "unit_amount_minor", "created_at",
                "expires_at",
            ])
        let v = try decoder.container(keyedBy: CodingKeys.self)
        id = try CommerceCoding.resource(v.decode(String.self, forKey: .id))
        revision = try v.decode(Int.self, forKey: .revision)
        scope = try v.decode(OrdersWorkspaceScope.self, forKey: .scope)
        merchantID = try CommerceCoding.merchantID(v.decode(String.self, forKey: .merchantID))
        productClassification = try v.decode(MerchantCategory.self, forKey: .productClassification)
        name = try v.decode(String.self, forKey: .name)
        description = try v.decode(String.self, forKey: .description)
        photoURL = try CommerceCoding.photo(v.decodeIfPresent(String.self, forKey: .photoURL))
        currency = try v.decode(String.self, forKey: .currency)
        unitAmountMinor = try v.decode(Int64.self, forKey: .unitAmountMinor)
        createdAt = try CommerceCoding.date(v.decode(String.self, forKey: .createdAt))
        expiresAt = try v.decodeIfPresent(String.self, forKey: .expiresAt).map(CommerceCoding.date)
        guard (1...200).contains(name.unicodeScalars.count),
            (1...2000).contains(description.unicodeScalars.count),
            name.contains(where: { !$0.isWhitespace }),
            description.contains(where: { !$0.isWhitespace }),
            expiresAt == nil || expiresAt! > createdAt
        else { throw CommerceModelError.invalidResource }
        guard revision == 1, currency == "USD", unitAmountMinor >= 1, unitAmountMinor <= 99_999_999
        else {
            throw CommerceModelError.invalidAmount
        }
    }
}

public struct SaleOrder: Decodable, Equatable, Sendable {
    public let id: String
    public let revision: Int
    public let scope: OrdersWorkspaceScope
    public let offerID: String
    public let offerRevision: Int
    public let variantID: String
    public let merchantID: UUID
    public let productClassification: MerchantCategory
    public let quantity: Int64
    public let currency: String
    public let unitAmountMinor: Int64
    public let amountMinor: Int64
    public let amountSource: String
    public let createdAt: Date

    enum CodingKeys: String, CodingKey, CaseIterable {
        case id, revision, scope
        case offerID = "offer_id"
        case offerRevision = "offer_revision"
        case variantID = "variant_id"
        case merchantID = "merchant_id"
        case productClassification = "product_classification"
        case quantity, currency
        case unitAmountMinor = "unit_amount_minor"
        case amountMinor = "amount_minor"
        case amountSource = "amount_source"
        case createdAt = "created_at"
    }

    public init(from decoder: any Decoder) throws {
        try CommerceCoding.exactKeys(
            decoder,
            [
                "id", "revision", "scope", "offer_id", "offer_revision", "variant_id",
                "merchant_id", "product_classification", "quantity", "currency",
                "unit_amount_minor", "amount_minor", "amount_source", "created_at",
            ])
        let v = try decoder.container(keyedBy: CodingKeys.self)
        id = try CommerceCoding.resource(v.decode(String.self, forKey: .id))
        revision = try v.decode(Int.self, forKey: .revision)
        scope = try v.decode(OrdersWorkspaceScope.self, forKey: .scope)
        offerID = try CommerceCoding.resource(v.decode(String.self, forKey: .offerID))
        offerRevision = try v.decode(Int.self, forKey: .offerRevision)
        variantID = try CommerceCoding.resource(v.decode(String.self, forKey: .variantID))
        merchantID = try CommerceCoding.merchantID(v.decode(String.self, forKey: .merchantID))
        productClassification = try v.decode(MerchantCategory.self, forKey: .productClassification)
        quantity = try v.decode(Int64.self, forKey: .quantity)
        currency = try v.decode(String.self, forKey: .currency)
        unitAmountMinor = try v.decode(Int64.self, forKey: .unitAmountMinor)
        amountMinor = try v.decode(Int64.self, forKey: .amountMinor)
        amountSource = try v.decode(String.self, forKey: .amountSource)
        createdAt = try CommerceCoding.date(v.decode(String.self, forKey: .createdAt))
        guard revision == 1, offerRevision == 1, variantID == offerID, currency == "USD",
            amountSource == "catalog_offer_revision", quantity >= 1, quantity <= 10_000,
            unitAmountMinor >= 1, unitAmountMinor <= 99_999_999,
            amountMinor >= 1, amountMinor <= 99_999_999,
            quantity <= Int64.max / unitAmountMinor, amountMinor == quantity * unitAmountMinor
        else {
            throw CommerceModelError.invalidAmount
        }
    }
}

public struct CatalogOfferPage: Decodable, Equatable, Sendable {
    public let items: [CatalogOffer]
    public let nextCursor: String?

    enum CodingKeys: String, CodingKey, CaseIterable {
        case items
        case nextCursor = "next_cursor"
    }

    public init(from decoder: any Decoder) throws {
        try CommerceCoding.exactKeys(decoder, ["items", "next_cursor"])
        let values = try decoder.container(keyedBy: CodingKeys.self)
        items = try values.decode([CatalogOffer].self, forKey: .items)
        nextCursor = try values.decodeIfPresent(String.self, forKey: .nextCursor).map(
            CommerceCoding.resource)
    }
}

public struct SaleOrderPage: Decodable, Equatable, Sendable {
    public let items: [SaleOrder]
    public let nextCursor: String?

    enum CodingKeys: String, CodingKey, CaseIterable {
        case items
        case nextCursor = "next_cursor"
    }

    public init(from decoder: any Decoder) throws {
        try CommerceCoding.exactKeys(decoder, ["items", "next_cursor"])
        let values = try decoder.container(keyedBy: CodingKeys.self)
        items = try values.decode([SaleOrder].self, forKey: .items)
        nextCursor = try values.decodeIfPresent(String.self, forKey: .nextCursor).map(
            CommerceCoding.resource)
    }
}
