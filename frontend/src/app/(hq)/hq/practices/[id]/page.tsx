import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { HqPracticeScreen } from "@/features/hq/practice/HqPracticeScreen";
import { HQ_TEXT } from "@/features/hq/strings";

export const metadata: Metadata = { title: HQ_TEXT.practice.title };

export default async function HqPracticePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense fallback={<LoadingState label={HQ_TEXT.practice.loading} />}>
      <HqPracticeScreen practiceId={id} />
    </Suspense>
  );
}
