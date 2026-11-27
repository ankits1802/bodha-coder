import type { Metadata } from "next";
import { Suspense } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { LoadingState } from "@/components/ui/LoadingState";
import { PlanScreen } from "@/features/plan/PlanScreen";
import { PLAN_TEXT } from "@/features/plan/strings";

export const metadata: Metadata = { title: PLAN_TEXT.title };

export default function PlanPage() {
  return (
    <AreaGuard area="plan">
      <Suspense fallback={<LoadingState label={PLAN_TEXT.loading} />}>
        <PlanScreen />
      </Suspense>
    </AreaGuard>
  );
}
