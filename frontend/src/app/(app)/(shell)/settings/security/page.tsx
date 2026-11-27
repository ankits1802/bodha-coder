import type { Metadata } from "next";
import { Suspense } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { LoadingState } from "@/components/ui/LoadingState";
import { PracticeSecurityScreen } from "@/features/security/PracticeSecurityScreen";
import { SECURITY_TEXT } from "@/features/security/strings";

export const metadata: Metadata = { title: SECURITY_TEXT.title };

export default function PracticeSecurityPage() {
  return (
    <AreaGuard area="security">
      <Suspense fallback={<LoadingState label={SECURITY_TEXT.loading} />}>
        <PracticeSecurityScreen />
      </Suspense>
    </AreaGuard>
  );
}
