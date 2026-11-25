import type { Metadata } from "next";
import { Suspense } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { LoadingState } from "@/components/ui/LoadingState";
import { SetupScreen } from "@/features/setup/SetupScreen";
import { SETUP_TEXT } from "@/features/setup/strings";

export const metadata: Metadata = { title: SETUP_TEXT.title };

export default function SetupPage() {
  return (
    <AreaGuard area="setup">
      <Suspense fallback={<LoadingState label={SETUP_TEXT.loading} />}>
        <SetupScreen />
      </Suspense>
    </AreaGuard>
  );
}
