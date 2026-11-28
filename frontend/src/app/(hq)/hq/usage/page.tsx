import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { HqUsageScreen } from "@/features/hq/usage/HqUsageScreen";
import { HQ_TEXT } from "@/features/hq/strings";

export const metadata: Metadata = { title: HQ_TEXT.usage.title };

export default function HqUsagePage() {
  return (
    <Suspense fallback={<LoadingState label={HQ_TEXT.usage.loading} />}>
      <HqUsageScreen />
    </Suspense>
  );
}
