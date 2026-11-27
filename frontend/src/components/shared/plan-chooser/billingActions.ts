import type { CheckoutRequest, RedirectLink } from "@/lib/api/types";

export interface BillingActions {
  checkout: (body: CheckoutRequest) => Promise<RedirectLink>;
  portal: () => Promise<RedirectLink>;
  cancel: () => Promise<void>;
}
