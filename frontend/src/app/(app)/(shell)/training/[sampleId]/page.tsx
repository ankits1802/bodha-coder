import type { Metadata } from "next";
import { Suspense } from "react";
import { TrainingReviewScreen } from "@/features/training/TrainingReviewScreen";
import { TRAINING_TEXT } from "@/features/training/strings";

export const metadata: Metadata = { title: TRAINING_TEXT.reviewTitle };

export default async function TrainingReviewPage({ params }: { params: Promise<{ sampleId: string }> }) {
  const { sampleId } = await params;
  return (
    <Suspense fallback={null}>
      <TrainingReviewScreen sampleId={sampleId} />
    </Suspense>
  );
}
