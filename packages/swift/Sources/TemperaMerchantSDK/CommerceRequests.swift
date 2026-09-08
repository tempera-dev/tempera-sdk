import Foundation

/// A declared catalog offer. It carries no payment, payout, or provider authority.
public struct CreateCatalogOfferInput: Sendable, Equatable {
    public let productClassification: MerchantCategory
    public let name: String
    public let description: String
    public let photoURL: URL?
    public let unitAmountMinor: Int64
    public let expiresAt: Date?

    public init(
        productClassification: MerchantCategory,
        name: String,
        description: String,
        photoURL: URL? = nil,
        unitAmountMinor: Int64,
        expiresAt: Date? = nil
    ) throws {
        guard CommerceRequestValidation.nonblank(name, maximumScalars: 200),
            CommerceRequestValidation.nonblank(description, maximumScalars: 2_000),
            (1...99_999_999).contains(unitAmountMinor),
            try CommerceRequestValidation.photo(photoURL)
        else {
            throw CommerceModelError.invalidResource
        }
        if let expiresAt {
            guard let normalizedExpiry = CommerceRequestValidation.normalizedDate(expiresAt) else {
                throw CommerceModelError.invalidResource
            }
            self.expiresAt = normalizedExpiry
        } else {
            self.expiresAt = nil
        }
        self.productClassification = productClassification
        self.name = name
        self.description = description
        self.photoURL = photoURL
        self.unitAmountMinor = unitAmountMinor
    }

    /// The canonical UTC representation used in the request body and for comparing its response.
    var encodedExpiresAt: String? { expiresAt.map(CommerceRequestValidation.rfc3339) }

    /// `merchantID` is supplied by the authenticated merchant session, never by the caller input.
    func encoded(merchantID: UUID) throws -> Data {
        guard CommerceRequestValidation.merchantID(merchantID) else {
            throw CommerceModelError.invalidMerchantID
        }
        let wire = Wire(
            merchantID: merchantID.uuidString.lowercased(),
            productClassification: productClassification.rawValue,
            name: name,
            description: description,
            photoURL: photoURL?.absoluteString,
            currency: "USD",
            unitAmountMinor: unitAmountMinor,
            expiresAt: encodedExpiresAt
        )
        return try CommerceRequestValidation.encode(wire)
    }

    private struct Wire: Encodable {
        let merchantID: String
        let productClassification: String
        let name: String
        let description: String
        let photoURL: String?
        let currency: String
        let unitAmountMinor: Int64
        let expiresAt: String?

        enum CodingKeys: String, CodingKey {
            case merchantID = "merchant_id"
            case productClassification = "product_classification"
            case name, description
            case photoURL = "photo_url"
            case currency
            case unitAmountMinor = "unit_amount_minor"
            case expiresAt = "expires_at"
        }
    }
}

/// A revision-one declared sale order. The server resolves offer pricing and merchant binding.
public struct CreateSaleOrderInput: Sendable, Equatable {
    public let offerID: String
    public let offerRevision: Int
    public let quantity: Int64

    public init(offerID: String, quantity: Int64) throws {
        guard CommerceRequestValidation.resourceID(offerID), (1...10_000).contains(quantity) else {
            throw CommerceModelError.invalidAmount
        }
        self.offerID = offerID
        self.offerRevision = 1
        self.quantity = quantity
    }

    func encoded() throws -> Data {
        try CommerceRequestValidation.encode(
            Wire(
                offerID: offerID, offerRevision: offerRevision, quantity: quantity))
    }

    private struct Wire: Encodable {
        let offerID: String
        let offerRevision: Int
        let quantity: Int64

        enum CodingKeys: String, CodingKey {
            case offerID = "offer_id"
            case offerRevision = "offer_revision"
            case quantity
        }
    }
}

private enum CommerceRequestValidation {
    static func nonblank(_ value: String, maximumScalars: Int) -> Bool {
        let scalars = value.unicodeScalars
        return !scalars.isEmpty && scalars.count <= maximumScalars
            && scalars.contains { !CharacterSet.whitespacesAndNewlines.contains($0) }
    }

    static func resourceID(_ value: String) -> Bool {
        let scalars = value.unicodeScalars
        guard !scalars.isEmpty, scalars.count <= 128,
            let match = value.range(
                of: "^[A-Za-z0-9][A-Za-z0-9_.-]*$", options: .regularExpression)
        else { return false }
        return match == value.startIndex..<value.endIndex
    }

    static func merchantID(_ value: UUID) -> Bool {
        let text = value.uuidString.lowercased()
        let bytes = Array(text.utf8)
        guard bytes.count == 36, (49...56).contains(bytes[14]) else { return false }
        return [56, 57, 97, 98].contains(bytes[19])
    }

    static func photo(_ value: URL?) throws -> Bool {
        guard let value else { return true }
        let text = value.absoluteString
        guard text.unicodeScalars.count <= 2_048, text.hasPrefix("https://"),
            !text.unicodeScalars.contains(where: CharacterSet.whitespacesAndNewlines.contains),
            let components = URLComponents(url: value, resolvingAgainstBaseURL: false),
            components.scheme == "https", components.host?.isEmpty == false,
            components.user == nil, components.password == nil, components.fragment == nil
        else { return false }
        return true
    }

    static func normalizedDate(_ value: Date) -> Date? {
        guard value.timeIntervalSinceReferenceDate.isFinite else { return nil }
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        let components = calendar.dateComponents([.era, .year], from: value)
        guard components.era == 1, let year = components.year, (1...9999).contains(year) else {
            return nil
        }
        let formatter = rfc3339Formatter()
        return formatter.date(from: formatter.string(from: value))
    }

    static func rfc3339(_ value: Date) -> String { rfc3339Formatter().string(from: value) }

    private static func rfc3339Formatter() -> ISO8601DateFormatter {
        let formatter = ISO8601DateFormatter()
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }

    static func encode<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return try encoder.encode(value)
    }
}
