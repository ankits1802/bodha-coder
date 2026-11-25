import type { Metadata } from "next";
import { Suspense } from "react";
import { InsightsScreen } from "@/features/insights/InsightsScreen";
import { INSIGHTS_TEXT } from "@/features/insights/strings";

export const metadata: Metadata = { title: INSIGHTS_TEXT.title };

export default function InsightsPage() {
  return (
    <Suspense>
      <InsightsScreen />
    </Suspense>
  );
}
