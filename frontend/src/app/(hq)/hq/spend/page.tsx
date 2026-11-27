import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { HqSpendScreen } from "@/features/hq/spend/HqSpendScreen";
import { HQ_TEXT } from "@/features/hq/strings";

export const metadata: Metadata = { title: HQ_TEXT.spend.title };

export default function HqSpendPage() {
  return (
    <Suspense fallback={<LoadingState label={HQ_TEXT.spend.loading} />}>
      <HqSpendScreen />
    </Suspense>
  );
}
