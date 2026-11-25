import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { HqPracticesScreen } from "@/features/hq/practices/HqPracticesScreen";
import { HQ_TEXT } from "@/features/hq/strings";

export const metadata: Metadata = { title: HQ_TEXT.practices.title };

export default function HqPracticesPage() {
  return (
    <Suspense fallback={<LoadingState label={HQ_TEXT.practices.loading} />}>
      <HqPracticesScreen />
    </Suspense>
  );
}
