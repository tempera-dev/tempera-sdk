import Foundation
import XCTest

@testable import TemperaMerchantSDK

final class CommerceModelsTests: XCTestCase {
    private let scope = """
        {"organizationId":"merchant-a","projectId":"orders","environment":"test","siteId":"store-a"}
        """
    private let merchant = "018f3b2a-cc59-7b60-9c18-836c07d1f9d9"

    private func offer(_ changes: String = "") -> Data {
        Data(
            """
            {"id":"offer-1","revision":1,"scope":\(scope),"merchantId":"\(merchant)","productClassification":"physical_goods","name":"Widget","description":"Declared offer","photoUrl":null,"currency":"USD","unitAmountMinor":1200,"createdAt":"2026-09-05T12:00:00Z","expiresAt":null\(changes)}
            """.utf8)
    }

    private func sale(_ changes: String = "") -> Data {
        Data(
            """
            {"id":"sale-1","revision":1,"scope":\(scope),"offerId":"offer-1","offerRevision":1,"variantId":"offer-1","merchantId":"\(merchant)","productClassification":"physical_goods","quantity":2,"currency":"USD","unitAmountMinor":1200,"amountMinor":2400,"amountSource":"catalog_offer_revision","createdAt":"2026-09-05T12:00:00Z"\(changes)}
            """.utf8)
    }

    private func changed(_ data: Data, _ old: String, _ new: String) -> Data {
        Data(String(data: data, encoding: .utf8)!.replacingOccurrences(of: old, with: new).utf8)
    }

    private func actualFixture() throws -> (Data, Data) {
        let url = try XCTUnwrap(
            Bundle.module.url(
                forResource: "orders-commerce", withExtension: "json", subdirectory: "Fixtures"))
        let root = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
        let responses = root["responses"] as! [String: Any]
        return (
            try JSONSerialization.data(withJSONObject: responses["offer"]!),
            try JSONSerialization.data(withJSONObject: responses["order"]!)
        )
    }

    func testDecodesCanonicalOfferAndSaleOrder() throws {
        let decoder = JSONDecoder()
        let (offerData, saleData) = try actualFixture()
        let decodedOffer = try decoder.decode(CatalogOffer.self, from: offerData)
        XCTAssertEqual(decodedOffer.id, "00000000-0000-4000-8000-000000000001")
        XCTAssertEqual(decodedOffer.scope.environment, .test)
        XCTAssertEqual(
            decodedOffer.merchantID.uuidString.lowercased(), "12345678-1234-4123-8123-123456789abc")
        XCTAssertNil(decodedOffer.photoURL)

        let decodedSale = try decoder.decode(SaleOrder.self, from: saleData)
        XCTAssertEqual(decodedSale.offerID, decodedSale.variantID)
        XCTAssertEqual(decodedSale.amountMinor, 3600)
        XCTAssertEqual(decodedSale.amountSource, "catalog_offer_revision")
    }

    func testPagesRequireItemsAndPreserveNullableCursor() throws {
        let decoder = JSONDecoder()
        let offerJSON = String(data: offer(), encoding: .utf8)!
        let pageJSON = "{\"items\":[\(offerJSON)],\"nextPageToken\":null}"
        let page = try decoder.decode(CatalogOfferPage.self, from: Data(pageJSON.utf8))
        XCTAssertEqual(page.items.count, 1)
        XCTAssertNil(page.nextPageToken)
        XCTAssertThrowsError(try decoder.decode(CatalogOfferPage.self, from: Data("{}".utf8)))
    }

    func testRejectsUnknownFieldsAndUnsafePhotoURL() throws {
        let decoder = JSONDecoder()
        XCTAssertThrowsError(
            try decoder.decode(CatalogOffer.self, from: offer(",\"unexpected\":true")))
        XCTAssertThrowsError(
            try decoder.decode(
                CatalogOffer.self,
                from: changed(
                    offer(), "\"photoUrl\":null", "\"photoUrl\":\"http://example.test/p.png\"")))
    }

    func testRejectsMerchantAndResourceAndScopeViolations() throws {
        let decoder = JSONDecoder()
        XCTAssertThrowsError(
            try decoder.decode(
                CatalogOffer.self,
                from: changed(
                    offer(), "018f3b2a-cc59-7b60-9c18-836c07d1f9d9",
                    "018f3b2a-cc59-9b60-9c18-836c07d1f9d9")))
        XCTAssertThrowsError(
            try decoder.decode(CatalogOffer.self, from: changed(offer(), "offer-1", "bad/id")))
        XCTAssertThrowsError(
            try decoder.decode(
                CatalogOffer.self,
                from: changed(offer(), "\"environment\":\"test\"", "\"environment\":\"unknown\"")))
    }

    func testRejectsSaleAmountMismatchAndOverflowBounds() throws {
        let decoder = JSONDecoder()
        XCTAssertThrowsError(
            try decoder.decode(
                SaleOrder.self,
                from: changed(sale(), "\"amountMinor\":2400", "\"amountMinor\":2401")))
        XCTAssertThrowsError(
            try decoder.decode(
                SaleOrder.self,
                from: changed(sale(), "\"variantId\":\"offer-1\"", "\"variantId\":\"different\""))
        )
        XCTAssertThrowsError(
            try decoder.decode(
                SaleOrder.self, from: changed(sale(), "\"quantity\":2", "\"quantity\":10001")))
    }

    func testRejectsRequiredFieldAndScalarBoundaryPoisons() throws {
        let decoder = JSONDecoder()
        for (old, new) in [
            ("\"revision\":1", "\"revision\":true"),
            ("\"unitAmountMinor\":1200", "\"unitAmountMinor\":1200.5"),
            ("\"unitAmountMinor\":1200", "\"unitAmountMinor\":9999999999999999999999"),
            ("\"name\":\"Widget\"", "\"name\":\" \""),
            ("\"description\":\"Declared offer\"", "\"description\":\"\""),
            ("\"photoUrl\":null,", ""),
            ("\"expiresAt\":null", "\"expiresAt\":\"2026-09-04T00:00:00Z\""),
            ("2026-09-05T12:00:00Z", "2026-09-05T12:00:00Zjunk"),
            ("2026-09-05T12:00:00Z", "2026-02-30T12:00:00Z"),
            ("offer-1", "offer-1\\n"),
        ] {
            XCTAssertThrowsError(
                try decoder.decode(CatalogOffer.self, from: changed(offer(), old, new)), new)
        }
        XCTAssertThrowsError(
            try decoder.decode(SaleOrder.self, from: changed(sale(), "sale-1", "bad/id")))
        XCTAssertThrowsError(try decoder.decode(SaleOrder.self, from: sale(",\"extra\":true")))
        XCTAssertThrowsError(
            try decoder.decode(
                CatalogOfferPage.self, from: Data("{\"items\":[],\"nextPageToken\":\"../bad\"}".utf8))
        )
        XCTAssertThrowsError(
            try decoder.decode(
                OrdersWorkspaceScope.self,
                from: Data(
                    "{\"organizationId\":\"a\",\"projectId\":\"b\",\"environment\":\"test\",\"siteId\":\"c\",\"extra\":true}"
                        .utf8)))
    }
}
