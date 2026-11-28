"use client";

import type { ReactNode } from "react";
import { KeyHint } from "@/components/shared/shortcuts/KeyHint";
import { Button } from "@/components/ui/Button";
import type { NoteDetail } from "@/lib/api/types";
import type { ReviewPermissions } from "../permissions";
import { REVIEW_TEXT } from "../strings";
import { APPROVE_TARGET } from "../useFindingFocus";
import type { ReviewActions } from "../useReviewActions";
import { EstimateSummary } from "./ClaimEstimate";
import { LinkedClaimCodes } from "./LinkedClaimCodes";

interface ClaimBarProps {
  detail: NoteDetail;
  permissions: ReviewPermissions;
  actions: ReviewActions;
  questionCount: number;
  onAsk: () => void;
  onFlag: () => void;
  onKeep: () => void;
  onReturn: () => void;
}

function ComplianceButtons({ detail, actions, onKeep, onReturn }: Pick<ClaimBarProps, "detail" | "actions" | "onKeep" | "onReturn">) {
  const words = REVIEW_TEXT.actions;
  const em = detail.findings.find((finding) => finding.kind === "em");
  const billed = em?.code_before ?? null;
  const supported = em?.code_after ?? null;
  return (
    <>
      <Button variant="plain" className="text-secondary" onClick={onKeep} disabled={actions.pending}>
        {billed ? words.keepBilled(billed) : words.keepPlain}
      </Button>
      <Button onClick={onReturn} disabled={actions.pending}>
        {words.returnToCoder}
      </Button>
      <Button variant="primary" onClick={() => void actions.decideCompliance("confirm", null)} pending={actions.pending}>
        {supported ? words.confirm(supported) : words.confirmPlain}
      </Button>
    </>
  );
}

function CoderButtons({ detail, permissions, actions, questionCount, onAsk }: Omit<ClaimBarProps, "onFlag" | "onKeep" | "onReturn">) {
  const words = REVIEW_TEXT.actions;
  const asking = permissions.ask && questionCount > 0;
  return (
    <>
      {permissions.approve ? (
        <Button
          variant={asking ? "secondary" : "primary"}
          data-target={APPROVE_TARGET}
          onClick={() => void actions.approve()}
          pending={actions.pending}
        >
          {asking ? words.approveWithoutAsking : words.approve} <KeyHint shortcut="approve" onPrimary={!asking} />
        </Button>
      ) : null}
      {asking ? (
        <Button variant="primary" onClick={onAsk}>
          {words.askProvider(detail.note.provider.name, questionCount)} <KeyHint shortcut="askProvider" onPrimary />
        </Button>
      ) : null}
    </>
  );
}

export function ClaimBar(props: ClaimBarProps) {
  const { detail, permissions, actions, onFlag } = props;
  let buttons: ReactNode = null;
  if (permissions.compliance) buttons = <ComplianceButtons {...props} />;
  else if (permissions.approve || permissions.ask) buttons = <CoderButtons {...props} />;
  return (
    <div data-usage-step="claim" className="sticky bottom-0 z-10 -mx-4 border-t border-separator bg-surface/95 sm:-mx-8">
      <div className="mx-auto flex max-w-review flex-wrap items-center justify-between gap-3.5 px-4 py-3 sm:px-8">
        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex min-w-0 flex-wrap items-center gap-1.5">
            <span className="mr-1 text-subhead text-secondary">{REVIEW_TEXT.claim}</span>
            {detail.claim.length > 0 ? (
              <LinkedClaimCodes
                noteId={detail.note.id}
                claim={detail.claim}
                estimate={detail.estimate}
                editable={permissions.decide}
              />
            ) : (
              <span className="text-subhead text-tertiary">{REVIEW_TEXT.claimEmpty}</span>
            )}
          </div>
          {detail.estimate ? <EstimateSummary estimate={detail.estimate} /> : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {actions.error ? <span role="alert" className="text-footnote text-bad-text">{actions.error}</span> : null}
          {permissions.flag ? (
            <Button variant="danger" onClick={onFlag}>
              {REVIEW_TEXT.actions.flag}
            </Button>
          ) : null}
          {buttons}
        </div>
      </div>
    </div>
  );
}
