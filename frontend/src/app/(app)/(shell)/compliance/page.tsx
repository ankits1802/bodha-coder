import type { Metadata } from "next";
import { Suspense } from "react";
import { ComplianceScreen } from "@/features/compliance/ComplianceScreen";
import { COMPLIANCE_TEXT } from "@/features/compliance/strings";

export const metadata: Metadata = { title: COMPLIANCE_TEXT.title };

export default function CompliancePage() {
  return (
    <Suspense>
      <ComplianceScreen />
    </Suspense>
  );
}
