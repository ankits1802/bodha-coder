"use client";

import { useId } from "react";
import { RemoteView } from "@/components/ui/RemoteView";
import { ClaimCheckList } from "./ClaimCheckList";
import { claimCheckItems } from "./claimCheckItems";
import { CLAIM_CHECK_TEXT } from "./strings";
import { useClaimChecks } from "./useClaimChecks";

const REMOTE_TEXT = { loading: CLAIM_CHECK_TEXT.loading, empty: CLAIM_CHECK_TEXT.clean, retry: CLAIM_CHECK_TEXT.retry };

interface ClaimChecksPanelProps {
  noteId: string;
  claim: string[];
}

export function ClaimChecksPanel({ noteId, claim }: ClaimChecksPanelProps) {
  const checks = useClaimChecks(noteId, claim);
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-2 border-t border-hairline px-5 py-4">
      <h3 id={headingId} className="m-0 font-sans text-subhead font-semibold text-secondary">
        {CLAIM_CHECK_TEXT.heading}
      </h3>
      <RemoteView state={checks.state} text={REMOTE_TEXT} onRetry={checks.reload}>
        {(data) => <ClaimCheckList items={claimCheckItems(data)} />}
      </RemoteView>
    </section>
  );
}
