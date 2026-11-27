import type { Metadata } from "next";
import { Suspense } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { LoadingState } from "@/components/ui/LoadingState";
import { SecurityScreen } from "@/features/security/SecurityScreen";
import { SECURITY_TEXT } from "@/features/security/strings";

export const metadata: Metadata = { title: SECURITY_TEXT.accountTitle };

export default function AccountPage() {
  return (
    <AreaGuard area="account">
      <Suspense fallback={<LoadingState label={SECURITY_TEXT.loading} />}>
        <SecurityScreen />
      </Suspense>
    </AreaGuard>
  );
}
