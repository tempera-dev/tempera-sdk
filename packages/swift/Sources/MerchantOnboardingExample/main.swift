import Foundation
import TemperaMerchantSDK

@main struct Example {
  static func main() async {
    guard
      let origin = ProcessInfo.processInfo.environment["TEMPERA_PAYMENTS_ORIGIN"].flatMap(
        URL.init(string:)),
      let token = ProcessInfo.processInfo.environment["TEMPERA_USER_OAUTH_TOKEN"],
      let tenantID = ProcessInfo.processInfo.environment["TEMPERA_TENANT_ID"]
    else {
      print(
        "Set onboarding-provisioned TEMPERA_PAYMENTS_ORIGIN, TEMPERA_USER_OAUTH_TOKEN, and TEMPERA_TENANT_ID."
      )
      return
    }
    do {
      let client = try MerchantClient(origin: origin, bearerToken: { token })
      let merchant = try await client.workspaceMerchant(tenantID: tenantID)
      print("merchant=\(merchant.id) ready=\(merchant.isReady())")
    } catch { print(error.localizedDescription) }
  }
}
