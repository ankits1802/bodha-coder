"use client";

import { AreaGuard } from "@/components/shared/AreaGuard";
import { BlindCodingPanel } from "@/components/shared/blind-coding/BlindCodingPanel";
import { useBlindSession } from "@/components/shared/blind-coding/useBlindSession";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import type { BlindAnswer, BlindStep } from "@/lib/api/types";
import { QUALITY_TEXT } from "./strings";

const REMOTE_TEXT = { loading: QUALITY_TEXT.loading, empty: QUALITY_TEXT.allCoded, retry: QUALITY_TEXT.retry };

function BlindAudit({ sampleId }: { sampleId: string }) {
  const session = useBlindSession(sampleId);

  async function submit(itemId: string, answer: BlindAnswer): Promise<void> {
    if ((await session.submit.run(itemId, answer)).ok) session.step.reload();
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
        title={QUALITY_TEXT.blindTitle}
        actions={
          <ButtonLink href="/training" size="sm" variant="plain">
            {QUALITY_TEXT.assignedBack}
          </ButtonLink>
        }
      />
      {session.pdf.error ? <InlineAlert tone="bad">{session.pdf.error}</InlineAlert> : null}
      <RemoteView
        state={session.step.state}
        text={REMOTE_TEXT}
        isEmpty={(step: BlindStep) => step.item === null}
        onRetry={session.step.reload}
      >
        {renderStep}
      </RemoteView>
    </>
  );
}

export function BlindAuditScreen({ sampleId }: { sampleId: string }) {
  return (
    <AreaGuard area="queue">
      <BlindAudit key={sampleId} sampleId={sampleId} />
    </AreaGuard>
  );
}
