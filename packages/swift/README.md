# Tempera Merchant SDK (Swift)

This iOS 17/macOS 13 package uses Swift 6 and six merchant operations in the SDK's native transport contract: `workspace()`, `workspaceMerchant(tenantID:)`, `create`, `merchant`, `refresh`, and `onboarding`. The vendored contracts are pinned to reviewed, merged Payments and Auth Hub revisions in `specs/*.source`. Hosted access and provider qualification remain separate launch gates.

In Xcode, add `https://github.com/tempera-dev/tempera-sdk.git` as a package dependency, pin the reviewed SDK revision your application has accepted, and select the `TemperaMerchantSDK` product. The package manifest is at the repository root. It has no external package dependencies.

Create `MerchantClient` with an onboarding-provisioned HTTPS Payments origin and an injected async closure that returns a human user OAuth bearer token for each request. The package never requests, mints, stores, logs, or retries tokens; it asks only for the token already authorized with `payments:merchants:read` or `payments:merchants:write` for the requested operation.

Responses are capped at 256 KiB, redirects are denied, and onboarding URLs are validated as future-expiring `https://connect.stripe.com` links. Do not persist, cache, log, or prefetch them. `Merchant.isReady()` stays false for missing, future, or at-least-300-second-old provider observations.

From the SDK repository root, run `swift test`. The executable sample is source-only: `swift run merchant-onboarding-example` requires onboarding-provisioned `TEMPERA_PAYMENTS_ORIGIN`, `TEMPERA_USER_OAUTH_TOKEN`, and `TEMPERA_TENANT_ID`; without all three it performs no request.

After an interrupted create, reuse the original persisted idempotency key and unchanged request. `workspace()` recovers the authenticated workspace identity and an optional merchant without caller-supplied tenant input; `workspaceMerchant(tenantID:)` remains available where the caller already has an authoritative tenant. Refresh eligibility on foreground return from provider onboarding; returning to the app does not establish eligibility. Read HTTP status and error code from `MerchantClientError.server`, preserve uncertain operations for explicit recovery, and request a new onboarding-link key only after the previous link has expired or been consumed. Keep the existing workspace, payments-enabled, payouts-enabled and action-required states separate.

`MerchantStatusView` is an optional SwiftUI presentation component. Give it a `Merchant?` and a caller-owned async action closure; it displays workspace, payments, payouts, requirements, and next-step state without making network calls, storing credentials, or starting effects on appearance. It does not form a business, collect payment details, or issue payout receipts. The command-line example is not a checkout demonstration.

## Read offers and sale orders

`OrdersCommerceClient` provides `offers(after:limit:)`, `offer(id:)`, `saleOrders(after:limit:)`, and `saleOrder(id:)`. Configure it with the provisioned Orders HTTPS origin, exact four-part `OrdersWorkspaceScope`, and the merchant ID returned by authenticated Payments workspace recovery. Its token closure must return an OAuth token with `orders:read` for the `tempera-dropshipping` audience. A Payments token cannot be reused for Orders. Native grant eligibility and hosted access require separate admission.

```swift
let orders = try OrdersCommerceClient(
    origin: provisionedOrdersOrigin,
    scope: provisionedOrdersWorkspace,
    merchantID: authenticatedMerchant.id,
    bearerToken: { try await session.ordersReadToken() }
)
let page = try await orders.offers(limit: 50)
```

The caller owns the provisioning/session values in this example. Every response must match the configured workspace and merchant; individual reads must match the requested record ID. Models validate closed response fields, supported product categories, USD minor-unit bounds and sale-order amount consistency. Offer photos are display URLs; the client does not fetch them. Reads are bounded to 256 KiB, use fresh caller-supplied tokens, reject redirects and expose recovery errors through `OrdersCommerceError`. The client performs no automatic retry or write.

Offers and sale orders are declarations, so show them separately from verified payments, fees or payouts. This Swift client does not create offers/orders or consume the event projection. The generated TypeScript, Python and Rust operation registry separately includes the scoped event-projection read from the reviewed Orders source; it grants no Graph, MCP or provider admission.

The Swift tests decode actual local producer HTTP responses captured at the exact Orders source lock. To regenerate or verify that fixture with a clean producer checkout at the pinned commit, run `python3 scripts/export-swift-commerce-fixture.py --source-repo /path/to/pinned/orders --check` from the SDK root (omit `--check` to regenerate). The fixture uses a synthetic local principal and no provider effects. It does not qualify a real OAuth write grant or hosted TLS.

## Generated full-surface SDK (`TemperaSDK`)

`TemperaSDK` is a second, separate library product in the same package. It is
generated from `surface.json`, so it reaches every product and every typed
operation in the manifest -- not just the merchant commerce reads that
`TemperaMerchantSDK` publishes. The two targets are independent; neither
imports the other.

```swift
let auth = try TemperaAuth(issuerUrl: provisionedIssuer, apiKey: provisionedApiKey)
let client = try TemperaClient(auth: auth, environment: "staging")

let traces = try await client.palette.call("listTraces", ["tenantId": tenantID])
let useCases = try await client.dataEngine.call("listUseCases", ["parent": "projects/\(projectID)"])
try await client.tempo.request("/custom", method: "POST", body: ["note": "passthrough"])
```

`Sources/TemperaSDK/Surface.swift` is generated by
`python3 scripts/gen-sdk-surface.py` and must never be hand-edited. Everything
else in the target is the hand-written runtime: `URLSession` with async/await,
no external dependencies.

- **Parameters** accept the producer's canonical wire name or its snake_case
  alias, never both; requests always emit the canonical name.
- **Base URL precedence** is an explicit `baseUrls` override, then the
  product's environment variable, then the `environment:` preset.
- **Auth kinds**: `none`, `account` (the token `createHostedSession` returns),
  `product`, `oauthResource` (an operation-pinned audience), and
  `introspectionSecret`. PKCE is S256 and the audience travels as the RFC 8707
  `resource` parameter.
- **Timeout**: 30 seconds per attempt by default, configurable through
  `TemperaClientConfiguration(timeout:)`.
- **Retry**: at most 3 attempts, on 408, 429, 500, 502, 503, 504 and connection
  failures, with exponential backoff from 250 ms (doubling, capped at 8 s) and
  jitter that lands each delay uniformly in the top half of the band. A
  `Retry-After` header wins over the backoff and is capped at 30 seconds. Only
  operations the surface classifies `read` or `idempotent` are retried at all;
  a passthrough request follows its HTTP method, so POST and PATCH are sent
  exactly once. Every attempt resends identical bytes, so an idempotency key is
  never re-minted.
- **MCP**: `TemperaMcpClient` speaks the stateless `server/discover` lifecycle
  at protocol version `TemperaSurface.mcpProtocolVersion`.

Run its tests from the repository root with `swift test`, or
`swift test -Xswiftc -strict-concurrency=complete` to match CI.
