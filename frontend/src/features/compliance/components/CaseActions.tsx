"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { ReturnDialog } from "@/components/shared/return-reason/ReturnDialog";
import { useAction } from "@/hooks/useAction";
import { decideCompliance } from "@/lib/api/notes";
import type { ComplianceDecision } from "@/lib/api/types";
import type { CaseFacts } from "../complianceKinds";
import { COMPLIANCE_TEXT } from "../strings";
import { KeepDialog } from "./KeepDialog";

interface CaseActionsProps {
  noteId: string;
  facts: CaseFacts | null;
  canDecide: boolean;
  onDecided: (message: string) => void;
}

export function CaseActions({ noteId, facts, canDecide, onDecided }: CaseActionsProps) {
  const decide = useAction(decideCompliance);
  const [keeping, setKeeping] = useState(false);
  const [returning, setReturning] = useState(false);
  const changed = facts?.billed && facts.supported && facts.billed !== facts.supported;

  async function submit(decision: ComplianceDecision, reason: string | null): Promise<void> {
    const outcome = await decide.run(noteId, decision, reason);
    if (!outcome.ok) return;
    setKeeping(false);
    onDecided(COMPLIANCE_TEXT.decided[decision]);
  }

  return (
    <div className="flex flex-col gap-3 border-t border-hairline bg-footer-panel px-5 py-3.5">
      {decide.error && !keeping ? <InlineAlert tone="bad">{decide.error}</InlineAlert> : null}
      <div className="flex flex-wrap items-center gap-2">
        <ButtonLink href={`/notes/${encodeURIComponent(noteId)}?lane=compliance`} variant="plain">
          {COMPLIANCE_TEXT.openNote}
        </ButtonLink>
        <span className="flex-1" />
        {canDecide && facts ? (
          <>
            <Button variant="plain" disabled={decide.pending} onClick={() => setKeeping(true)}>
              {changed && facts.billed ? COMPLIANCE_TEXT.keep(facts.billed) : COMPLIANCE_TEXT.keepAsBilled}
            </Button>
            <Button disabled={decide.pending} onClick={() => setReturning(true)}>
              {COMPLIANCE_TEXT.returnToCoder}
            </Button>
            <Button variant="primary" pending={decide.pending && !keeping} onClick={() => void submit("confirm", null)}>
              {changed && facts.supported ? COMPLIANCE_TEXT.confirm(facts.supported) : COMPLIANCE_TEXT.confirmClaim}
            </Button>
          </>
        ) : null}
      </div>
      <KeepDialog
        open={keeping}
        pending={decide.pending}
        error={keeping ? decide.error : null}
        onClose={() => setKeeping(false)}
        onKeep={(reason) => void submit("keep", reason)}
      />
      {returning ? (
        <ReturnDialog
          noteId={noteId}
          onClose={() => setReturning(false)}
          onReturned={() => {
            setReturning(false);
            onDecided(COMPLIANCE_TEXT.decided.return);
          }}
        />
      ) : null}
    </div>
  );
}
