import type { Metadata } from "next";
import { Suspense } from "react";
import { BillingScreen } from "@/features/billing/BillingScreen";
import { BILLING_TEXT } from "@/features/billing/strings";

export const metadata: Metadata = { title: BILLING_TEXT.title };

export default function BillingPage() {
  return (
    <Suspense>
      <BillingScreen />
    </Suspense>
  );
}
