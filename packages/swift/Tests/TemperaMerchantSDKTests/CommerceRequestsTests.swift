import Foundation
import XCTest

@testable import TemperaMerchantSDK

final class CommerceRequestsTests: XCTestCase {
    private let merchantID = UUID(uuidString: "018f3b2a-cc59-7b60-9c18-836c07d1f9d9")!

    func testOfferWireIsStableAndMerchantIsInjectedOnlyAtEncoding() throws {
        let expiry = Date(timeIntervalSince1970: 1_800_000_000.123)
        let input = try CreateCatalogOfferInput(
            productClassification: .physicalGoods,
            name: "Replacement filter",
            description: "A declared physical replacement filter.",
            photoURL: try XCTUnwrap(URL(string: "https://cdn.example.test/filter.png?size=large")),
            unitAmountMinor: 1_250,
            expiresAt: expiry)

        let first = try input.encoded(merchantID: merchantID)
        XCTAssertEqual(first, try input.encoded(merchantID: merchantID))
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: first) as? [String: Any])
        XCTAssertEqual(
            Set(body.keys),
            [
                "merchant_id", "product_classification", "name", "description", "photo_url",
                "currency", "unit_amount_minor", "expires_at",
            ])
        XCTAssertEqual(body["merchant_id"] as? String, merchantID.uuidString.lowercased())
        XCTAssertEqual(body["currency"] as? String, "USD")
        XCTAssertEqual(body["unit_amount_minor"] as? Int, 1_250)
        XCTAssertEqual(body["expires_at"] as? String, input.encodedExpiresAt)
        XCTAssertTrue((input.encodedExpiresAt ?? "").hasSuffix("Z"))
        XCTAssertTrue((input.encodedExpiresAt ?? "").contains("."))
    }

    func testOfferOptionalValuesAreOmittedAndBoundsUseUnicodeScalars() throws {
        let boundaryName = String(repeating: "e\u{301}", count: 100)
        let input = try CreateCatalogOfferInput(
            productClassification: .offlineServices,
            name: boundaryName,
            description: "Declared service",
            unitAmountMinor: 99_999_999)
        let body = try XCTUnwrap(
            JSONSerialization.jsonObject(with: input.encoded(merchantID: merchantID))
                as? [String: Any])
        XCTAssertNil(body["photo_url"])
        XCTAssertNil(body["expires_at"])
        XCTAssertThrowsError(
            try CreateCatalogOfferInput(
                productClassification: .offlineServices,
                name: String(repeating: "e\u{301}", count: 101),
                description: "Declared service", unitAmountMinor: 1))
        XCTAssertThrowsError(
            try CreateCatalogOfferInput(
                productClassification: .offlineServices, name: " \n",
                description: "Declared service", unitAmountMinor: 1))
        XCTAssertThrowsError(
            try CreateCatalogOfferInput(
                productClassification: .offlineServices, name: "Service", description: "\t",
                unitAmountMinor: 1))
        XCTAssertThrowsError(
            try CreateCatalogOfferInput(
                productClassification: .offlineServices, name: "Service", description: "Declared",
                unitAmountMinor: 0))
        XCTAssertThrowsError(
            try CreateCatalogOfferInput(
                productClassification: .offlineServices, name: "Service", description: "Declared",
                unitAmountMinor: 100_000_000))
    }

    func testOfferRejectsUnsafePhotoAndNonProducerMerchantUUID() throws {
        XCTAssertThrowsError(
            try CreateCatalogOfferInput(
                productClassification: .physicalGoods, name: "Widget", description: "Declared",
                photoURL: try XCTUnwrap(URL(string: "http://cdn.example.test/widget.png")),
                unitAmountMinor: 1))
        XCTAssertThrowsError(
            try CreateCatalogOfferInput(
                productClassification: .physicalGoods, name: "Widget", description: "Declared",
                photoURL: try XCTUnwrap(URL(string: "https://user@example.test/widget.png")),
                unitAmountMinor: 1))
        let input = try CreateCatalogOfferInput(
            productClassification: .physicalGoods, name: "Widget", description: "Declared",
            unitAmountMinor: 1)
        XCTAssertThrowsError(
            try input.encoded(merchantID: UUID(uuidString: "00000000-0000-0000-0000-000000000000")!)
        )
    }

    func testSaleWireIsFixedRevisionAndRejectsInvalidInputs() throws {
        let input = try CreateSaleOrderInput(offerID: "offer-1", quantity: 10_000)
        XCTAssertEqual(input.offerRevision, 1)
        let first = try input.encoded()
        XCTAssertEqual(first, try input.encoded())
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: first) as? [String: Any])
        XCTAssertEqual(body["offer_id"] as? String, "offer-1")
        XCTAssertEqual(body["offer_revision"] as? Int, 1)
        XCTAssertEqual(body["quantity"] as? Int, 10_000)
        XCTAssertThrowsError(try CreateSaleOrderInput(offerID: "bad/id", quantity: 1))
        XCTAssertThrowsError(try CreateSaleOrderInput(offerID: "offer-1", quantity: 0))
        XCTAssertThrowsError(try CreateSaleOrderInput(offerID: "offer-1", quantity: 10_001))
    }
    func testExpiryIsCanonicalAndWithinProducerCalendar() throws {
        let original = Date(timeIntervalSince1970: 1_800_000_000.123456)
        let input = try CreateCatalogOfferInput(
            productClassification: .offlineServices, name: "Service",
            description: "Declared service", unitAmountMinor: 100, expiresAt: original)
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        XCTAssertEqual(formatter.date(from: try XCTUnwrap(input.encodedExpiresAt)), input.expiresAt)
        // Past values remain encodable for durable replay; admission is the producer's decision.
        XCTAssertNoThrow(
            try CreateCatalogOfferInput(
                productClassification: .offlineServices, name: "Service",
                description: "Declared service", unitAmountMinor: 100,
                expiresAt: Date(timeIntervalSince1970: 0)))
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        let beyond = try XCTUnwrap(
            calendar.date(from: DateComponents(year: 10000, month: 1, day: 1)))
        let before = try XCTUnwrap(
            calendar.date(from: DateComponents(era: 0, year: 1, month: 1, day: 1)))
        for date in [
            beyond, before, Date(timeIntervalSince1970: .infinity),
            Date(timeIntervalSince1970: .nan),
        ] {
            XCTAssertThrowsError(
                try CreateCatalogOfferInput(
                    productClassification: .offlineServices, name: "Service",
                    description: "Declared service", unitAmountMinor: 100, expiresAt: date))
        }
    }

}
