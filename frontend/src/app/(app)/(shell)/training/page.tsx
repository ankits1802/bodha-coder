import type { Metadata } from "next";
import { Suspense } from "react";
import { TrainingScreen } from "@/features/training/TrainingScreen";
import { TRAINING_TEXT } from "@/features/training/strings";

export const metadata: Metadata = { title: TRAINING_TEXT.title };

export default function TrainingPage() {
  return (
    <Suspense>
      <TrainingScreen />
    </Suspense>
  );
}
