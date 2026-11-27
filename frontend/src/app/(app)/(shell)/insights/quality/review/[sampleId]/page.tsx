import type { Metadata } from "next";
import { Suspense } from "react";
import { BlindAuditScreen } from "@/features/quality/BlindAuditScreen";
import { QUALITY_TEXT } from "@/features/quality/strings";

export const metadata: Metadata = { title: QUALITY_TEXT.blindTitle };

export default async function BlindAuditPage({ params }: { params: Promise<{ sampleId: string }> }) {
  const { sampleId } = await params;
  return (
    <Suspense fallback={null}>
      <BlindAuditScreen sampleId={sampleId} />
    </Suspense>
  );
}
