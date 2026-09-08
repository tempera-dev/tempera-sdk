#if canImport(SwiftUI)
    import XCTest
    @testable import TemperaMerchantSDK

    final class MerchantPresentationTests: XCTestCase {
        private let now = Date(timeIntervalSince1970: 1000)

        private func merchant(_ changes: [String: Any] = [:]) throws -> Merchant {
            var body: [String: Any] = [
                "id": "018f3210-9876-7123-8123-123456789abc", "tenantId": "org_example",
                "country": "US", "currency": "usd", "category": "offline_services",
                "workspaceReady": true, "paymentsEnabled": true, "payoutsEnabled": false,
                "actionRequired": false, "requirementsCurrent": true,
                "currentlyDue": [], "pastDue": [], "pendingVerification": [],
                "disabledReason": NSNull(), "nextAction": "ready", "providerObservedAt": 999,
            ]
            body.merge(changes) { _, new in new }
            return try JSONDecoder().decode(
                Merchant.self, from: JSONSerialization.data(withJSONObject: body))
        }

        func testNoMerchantSetsUpPayments() {
            let state = MerchantPresentationState(merchant: nil, now: now)
            XCTAssertEqual(state.action, .setupPayments)
            XCTAssertFalse(state.paymentsEnabled)
            XCTAssertFalse(state.payoutsEnabled)
            XCTAssertTrue(state.actionRequired)
        }

        func testPaymentAndPayoutEligibilityRemainSeparate() throws {
            let state = MerchantPresentationState(merchant: try merchant(), now: now)
            XCTAssertTrue(state.workspaceReady)
            XCTAssertTrue(state.paymentsEnabled)
            XCTAssertFalse(state.payoutsEnabled)
        }

        func testExactFreshnessBoundaryFutureAndMissingCannotDisplayEnabled() throws {
            let recent = MerchantPresentationState(
                merchant: try merchant(["providerObservedAt": 701]), now: now)
            XCTAssertTrue(recent.paymentsEnabled)
            for observed: Any in [700, 1001, NSNull()] {
                let state = MerchantPresentationState(
                    merchant: try merchant([
                        "providerObservedAt": observed, "payoutsEnabled": true,
                    ]),
                    now: now)
                XCTAssertFalse(state.paymentsEnabled)
                XCTAssertFalse(state.payoutsEnabled)
                XCTAssertTrue(state.actionRequired)
                XCTAssertEqual(state.action, .refreshStatus)
            }
        }

        func testProviderCurrentFlagCannotBeOverriddenByTimestamp() throws {
            let state = MerchantPresentationState(
                merchant: try merchant(["requirementsCurrent": false]), now: now)
            XCTAssertFalse(state.paymentsEnabled)
            XCTAssertTrue(state.actionRequired)
            XCTAssertEqual(state.action, .refreshStatus)
        }

        func testNextStepsRemainActionableAndSupportHoldIsPreserved() throws {
            XCTAssertEqual(
                MerchantPresentationState(
                    merchant: try merchant(["nextAction": "wait_for_provider"]), now: now
                ).action, .refreshStatus)
            XCTAssertEqual(
                MerchantPresentationState(
                    merchant: try merchant(["nextAction": "continue_onboarding"]), now: now
                ).action, .continueOnboarding)
            XCTAssertEqual(
                MerchantPresentationState(
                    merchant: try merchant([
                        "nextAction": "start_onboarding", "providerObservedAt": NSNull(),
                    ]), now: now
                ).action, .continueOnboarding)
            XCTAssertEqual(
                MerchantPresentationState(
                    merchant: try merchant([
                        "nextAction": "contact_support", "providerObservedAt": NSNull(),
                    ]), now: now
                ).action, .contactSupport)
        }
    }
#endif
