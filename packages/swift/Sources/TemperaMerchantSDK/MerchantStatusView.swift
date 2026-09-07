#if canImport(SwiftUI)
    import SwiftUI

    public enum MerchantStatusAction: Sendable {
        case setupPayments, continueOnboarding, refreshStatus, contactSupport
    }

    /// A display projection. It does not grant authority or establish payment proof.
    public struct MerchantPresentationState: Sendable, Equatable {
        public let workspaceReady: Bool
        public let paymentsEnabled: Bool
        public let payoutsEnabled: Bool
        public let actionRequired: Bool
        public let requirementsCurrent: Bool
        public let action: MerchantStatusAction
        public let detail: String

        public init(merchant: Merchant?, now: Date = Date()) {
            guard let merchant else {
                workspaceReady = false
                paymentsEnabled = false
                payoutsEnabled = false
                actionRequired = true
                requirementsCurrent = false
                action = .setupPayments
                detail = "Set up your payment-provider account to start onboarding."
                return
            }
            workspaceReady = merchant.workspaceReady
            let age = merchant.providerObservedAt.map {
                now.timeIntervalSince1970 - TimeInterval($0)
            }
            requirementsCurrent =
                merchant.requirementsCurrent && (age.map { $0 >= 0 && $0 < 300 } ?? false)
            paymentsEnabled = requirementsCurrent && merchant.paymentsEnabled
            payoutsEnabled = requirementsCurrent && merchant.payoutsEnabled
            actionRequired = merchant.actionRequired || !requirementsCurrent
            // No provider account exists yet, so refresh alone cannot start onboarding.
            if merchant.nextAction == .startOnboarding {
                action = .continueOnboarding
                detail = "Complete the provider's required information."
            } else if merchant.nextAction == .contactSupport {
                action = .contactSupport
                detail = "Support must review this account before onboarding can continue."
            } else if !requirementsCurrent {
                action = .refreshStatus
                detail =
                    "Refresh the provider status before relying on payment or payout eligibility."
            } else {
                switch merchant.nextAction {
                case .continueOnboarding:
                    action = .continueOnboarding
                    detail = "The provider needs more information."
                case .waitForProvider:
                    action = .refreshStatus
                    detail = "The provider is reviewing this account. You can check for an update."
                default:
                    action = .refreshStatus
                    detail =
                        "These are account eligibility states. Individual payments and bank payouts have separate receipts."
                }
            }
        }

        public var title: String {
            switch action {
            case .setupPayments: "Set up payments"
            case .continueOnboarding: "Continue onboarding"
            case .refreshStatus: "Refresh status"
            case .contactSupport: "Contact support"
            }
        }
    }

    /// Caller owns authentication, effects, persistence and error presentation.
    /// This view never sends a request merely because it appears.
    public struct MerchantStatusView: View {
        private let merchant: Merchant?
        private let action: @MainActor (MerchantStatusAction) async -> Void
        @State private var working = false

        public init(
            merchant: Merchant?, action: @escaping @MainActor (MerchantStatusAction) async -> Void
        ) {
            self.merchant = merchant
            self.action = action
        }

        public var body: some View {
            TimelineView(.periodic(from: .now, by: 1)) { context in
                let state = MerchantPresentationState(merchant: merchant, now: context.date)
                VStack(alignment: .leading, spacing: 12) {
                    Text("Payments").font(.headline)
                    status("Workspace ready", state.workspaceReady)
                    status("Payments enabled", state.paymentsEnabled)
                    status("Payouts enabled", state.payoutsEnabled)
                    status("Action required", state.actionRequired)
                    Text(state.detail).font(.callout).fixedSize(horizontal: false, vertical: true)
                    if let merchant {
                        let requirements = Array(Set(merchant.currentlyDue + merchant.pastDue))
                            .sorted()
                        if !requirements.isEmpty {
                            Text("Information requested").font(.subheadline.bold())
                            ForEach(requirements, id: \.self) { requirement in
                                Text(
                                    requirement.replacingOccurrences(of: "_", with: " ")
                                        .replacingOccurrences(
                                            of: ".", with: " · ")
                                )
                                .font(.caption).fixedSize(horizontal: false, vertical: true)
                            }
                        }
                        if !merchant.pendingVerification.isEmpty {
                            Text("Some information is awaiting provider verification.").font(
                                .caption)
                        }
                    }
                    Button {
                        guard !working else { return }
                        working = true
                        Task { @MainActor in
                            await action(state.action)
                            working = false
                        }
                    } label: {
                        HStack {
                            if working { ProgressView().controlSize(.small) }
                            Text(state.title)
                        }
                    }
                    .disabled(working)
                    .accessibilityLabel(state.title)
                }
                .accessibilityElement(children: .contain)
            }
        }

        private func status(_ label: String, _ value: Bool) -> some View {
            HStack(alignment: .firstTextBaseline) {
                Text(label)
                Spacer(minLength: 16)
                Text(value ? "Yes" : "No")
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("\(label): \(value ? "yes" : "no")")
        }
    }
#endif
