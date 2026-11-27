"use client";

import { useState } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { BlindCodingPanel } from "@/components/shared/blind-coding/BlindCodingPanel";
import { useBlindSession } from "@/components/shared/blind-coding/useBlindSession";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import type { BlindAnswer, BlindStep } from "@/lib/api/types";
import { FeedbackView } from "./components/FeedbackView";
import { TRAINING_TEXT } from "./strings";

const REMOTE_TEXT = { loading: TRAINING_TEXT.loading, empty: TRAINING_TEXT.allCoded, retry: TRAINING_TEXT.retry };

function TrainingReview({ sampleId }: { sampleId: string }) {
  const session = useBlindSession(sampleId);
  const [coded, setCoded] = useState<string | null>(null);

  async function submit(itemId: string, answer: BlindAnswer): Promise<void> {
    if ((await session.submit.run(itemId, answer)).ok) setCoded(itemId);
  }

  function next(): void {
    setCoded(null);
    session.step.reload();
  }

  function renderStep(step: BlindStep) {
    const item = step.item;
    if (item === null) return null;
    return (
      <BlindCodingPanel
        item={item}
        total={step.sample.total}
        pending={session.submit.pending}
        error={session.submit.error}
        pdfPending={session.pdf.pending}
        onSubmit={(answer) => void submit(item.id, answer)}
        onOpenPdf={() => void session.pdf.run(item.id)}
      />
    );
  }

  return (
    <>
      <PageHeader
        title={TRAINING_TEXT.reviewTitle}
        actions={
          <ButtonLink href="/training" size="sm" variant="plain">
            {TRAINING_TEXT.back}
          </ButtonLink>
        }
      />
      {session.pdf.error ? <InlineAlert tone="bad">{session.pdf.error}</InlineAlert> : null}
      {coded ? (
        <FeedbackView itemId={coded} onNext={next} />
      ) : (
        <RemoteView
          state={session.step.state}
          text={REMOTE_TEXT}
          isEmpty={(step: BlindStep) => step.item === null}
          onRetry={session.step.reload}
        >
          {renderStep}
        </RemoteView>
      )}
    </>
  );
}

export function TrainingReviewScreen({ sampleId }: { sampleId: string }) {
  return (
    <AreaGuard area="queue">
      <TrainingReview key={sampleId} sampleId={sampleId} />
    </AreaGuard>
  );
}
