import type { BillingActions } from "@/components/shared/plan-chooser/billingActions";
import { cancelOrganizationSubscription, openOrganizationPortal, startOrganizationCheckout } from "@/lib/api/organizations";

export function organizationBilling(organizationId: string): BillingActions {
  return {
    checkout: (body) => startOrganizationCheckout(organizationId, body),
    portal: () => openOrganizationPortal(organizationId),
    cancel: () => cancelOrganizationSubscription(organizationId),
  };
}
