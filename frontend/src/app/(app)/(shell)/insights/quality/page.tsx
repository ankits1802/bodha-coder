import type { Metadata } from "next";
import { Suspense } from "react";
import { QualityScreen } from "@/features/quality/QualityScreen";
import { QUALITY_TEXT } from "@/features/quality/strings";

export const metadata: Metadata = { title: QUALITY_TEXT.title };

export default function QualityPage() {
  return (
    <Suspense>
      <QualityScreen />
    </Suspense>
  );
}
