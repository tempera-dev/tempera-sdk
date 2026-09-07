#if canImport(SwiftUI)
    import XCTest
    @testable import TemperaMerchantSDK

    final class MerchantPresentationTests: XCTestCase {
        private let now = Date(timeIntervalSince1970: 1000)

        private func merchant(_ changes: [String: Any] = [:]) throws -> Merchant {
            var body: [String: Any] = [
                "id": "018f3210-9876-7123-8123-123456789abc", "tenant_id": "org_example",
                "country": "US", "currency": "usd", "category": "offline_services",
                "workspace_ready": true, "payments_enabled": true, "payouts_enabled": false,
                "action_required": false, "requirements_current": true,
                "currently_due": [], "past_due": [], "pending_verification": [],
                "disabled_reason": NSNull(), "next_action": "ready", "provider_observed_at": 999,
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
                merchant: try merchant(["provider_observed_at": 701]), now: now)
            XCTAssertTrue(recent.paymentsEnabled)
            for observed: Any in [700, 1001, NSNull()] {
                let state = MerchantPresentationState(
                    merchant: try merchant([
                        "provider_observed_at": observed, "payouts_enabled": true,
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
                merchant: try merchant(["requirements_current": false]), now: now)
            XCTAssertFalse(state.paymentsEnabled)
            XCTAssertTrue(state.actionRequired)
            XCTAssertEqual(state.action, .refreshStatus)
        }

        func testNextStepsRemainActionableAndSupportHoldIsPreserved() throws {
            XCTAssertEqual(
                MerchantPresentationState(
                    merchant: try merchant(["next_action": "wait_for_provider"]), now: now
                ).action, .refreshStatus)
            XCTAssertEqual(
                MerchantPresentationState(
                    merchant: try merchant(["next_action": "continue_onboarding"]), now: now
                ).action, .continueOnboarding)
            XCTAssertEqual(
                MerchantPresentationState(
                    merchant: try merchant([
                        "next_action": "start_onboarding", "provider_observed_at": NSNull(),
                    ]), now: now
                ).action, .continueOnboarding)
            XCTAssertEqual(
                MerchantPresentationState(
                    merchant: try merchant([
                        "next_action": "contact_support", "provider_observed_at": NSNull(),
                    ]), now: now
                ).action, .contactSupport)
        }
    }
#endif
