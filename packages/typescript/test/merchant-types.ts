// Compile the public package entry point, as an application developer does.
import { createTemperaClient, type TemperaPaymentsClient } from "../src/index.js";

const client = createTemperaClient();
const payments: TemperaPaymentsClient = client.temperaPayments;
void payments.getWorkspaceMerchant({ tenant_id: "org_example" });
void payments.createMerchant({ tenant_id: "org_example", country: "US", currency: "usd", category: "offline_services" });
void payments.getMerchant({ merchant_id: "example", tenant_id: "org_example" });
void payments.refreshMerchantEligibility({ merchant_id: "example", tenant_id: "org_example" });
void payments.createMerchantOnboardingLink({ merchant_id: "example", tenant_id: "org_example" }, {
  headers: { "Idempotency-Key": "persisted-request-key" },
});
// @ts-expect-error Only published operations are available on the typed client.
void payments.inventedMerchantOperation();
