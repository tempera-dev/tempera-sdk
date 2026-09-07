# Tempera Merchant SDK (Swift)

This iOS 17/macOS 13 package uses Swift 6 and the five merchant operations in the SDK's native transport contract. The vendored contracts are pinned to reviewed, merged Payments and Auth Hub revisions in `specs/*.source`. Hosted access and provider qualification remain separate launch gates.

In Xcode, add `https://github.com/tempera-dev/tempera-sdk.git` as a package dependency, pin the reviewed SDK revision your application has accepted, and select the `TemperaMerchantSDK` product. The package manifest is at the repository root. It has no external package dependencies.

Create `MerchantClient` with an onboarding-provisioned HTTPS Payments origin and an injected async closure that returns a human user OAuth bearer token for each request. The package never requests, mints, stores, logs, or retries tokens; it asks only for the token already authorized with `payments:merchants:read` or `payments:merchants:write` for the requested operation.

Responses are capped at 256 KiB, redirects are denied, and onboarding URLs are validated as future-expiring `https://connect.stripe.com` links. Do not persist, cache, log, or prefetch them. `Merchant.isReady()` stays false for missing, future, or at-least-300-second-old provider observations.

From the SDK repository root, run `swift test`. The executable sample is source-only: `swift run merchant-onboarding-example` requires onboarding-provisioned `TEMPERA_PAYMENTS_ORIGIN`, `TEMPERA_USER_OAUTH_TOKEN`, and `TEMPERA_TENANT_ID`; without all three it performs no request.

After an interrupted create, reuse the original persisted idempotency key and unchanged request. On app restart, `workspaceMerchant(tenantID:)` recovers the server's merchant ID. Refresh eligibility on foreground return from provider onboarding; returning to the app does not establish eligibility. Read HTTP status and error code from `MerchantClientError.server`, preserve uncertain operations for explicit recovery, and request a new onboarding-link key only after the previous link has expired or been consumed. Keep the existing workspace, payments-enabled, payouts-enabled and action-required states separate.

This first package slice covers onboarding only. SwiftUI components, order-bound checkout and a complete sample merchant app are subsequent integrations; the command-line example is not a checkout demonstration.
