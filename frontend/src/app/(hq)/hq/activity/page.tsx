import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { HqActivityScreen } from "@/features/hq/activity/HqActivityScreen";
import { HQ_TEXT } from "@/features/hq/strings";

export const metadata: Metadata = { title: HQ_TEXT.activity.title };

export default function HqActivityPage() {
  return (
    <Suspense fallback={<LoadingState label={HQ_TEXT.activity.loading} />}>
      <HqActivityScreen />
    </Suspense>
  );
}
