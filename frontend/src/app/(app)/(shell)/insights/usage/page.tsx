import type { Metadata } from "next";
import { Suspense } from "react";
import { UsageScreen } from "@/features/insights/UsageScreen";
import { INSIGHTS_TEXT } from "@/features/insights/strings";

export const metadata: Metadata = { title: INSIGHTS_TEXT.usage.title };

export default function UsagePage() {
  return (
    <Suspense>
      <UsageScreen />
    </Suspense>
  );
}
