import type { Metadata } from "next";
import { Suspense } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { LoadingState } from "@/components/ui/LoadingState";
import { AccessLogScreen } from "@/features/security/AccessLogScreen";
import { SECURITY_TEXT } from "@/features/security/strings";

export const metadata: Metadata = { title: SECURITY_TEXT.log.title };

export default function AccessLogPage() {
  return (
    <AreaGuard area="accessLog">
      <Suspense fallback={<LoadingState label={SECURITY_TEXT.log.loading} />}>
        <AccessLogScreen />
      </Suspense>
    </AreaGuard>
  );
}
