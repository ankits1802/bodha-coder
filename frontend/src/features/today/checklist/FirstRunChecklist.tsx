"use client";

import { useState } from "react";
import { InviteRowsDialog } from "@/components/shared/team-invite/InviteRowsDialog";
import { INVITE_ROWS_TEXT } from "@/components/shared/team-invite/strings";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/ErrorState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { TODAY_TEXT } from "../strings";
import { ChecklistRow } from "./ChecklistRow";
import { canHide, doneCount, nextStep } from "./checklistModel";
import { InlineChecks } from "./InlineChecks";
import { StepActions } from "./StepActions";
import { useChecklistActions } from "./useChecklistActions";
import type { FirstRun } from "./useFirstRun";

const TITLE_ID = "first-run-title";

export function FirstRunChecklist({ firstRun, lead }: { firstRun: FirstRun; lead: boolean }) {
  const actions = useChecklistActions(firstRun.reloadSetup);
  const [inviting, setInviting] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const words = TODAY_TEXT.checklist;
  if (firstRun.status === "error" && firstRun.error) {
    return (
      <Panel>
        <ErrorState message={firstRun.error} retryLabel={words.retry} onRetry={firstRun.retry} />
      </Panel>
    );
  }
  if (!firstRun.shown || !firstRun.setup) return null;
  const { steps, setup } = firstRun;
  const next = lead ? nextStep(steps) : null;
  const notice = actions.error ?? sent;
  const header = (
    <>
      <span className="text-subhead text-secondary tabular-nums">{words.progress(doneCount(steps), steps.length)}</span>
      {canHide(steps) ? (
        <Button size="sm" variant="plain" pending={actions.pending.hide} onClick={actions.hide}>
          {words.hide}
        </Button>
      ) : null}
    </>
  );

  return (
    <Panel aria-labelledby={TITLE_ID}>
      <PanelHeader title={<span id={TITLE_ID}>{words.title}</span>} actions={header} />
      {notice ? (
        <div className="px-4.5 pb-3">
          <InlineAlert tone={actions.error ? "bad" : "ok"}>{notice}</InlineAlert>
        </div>
      ) : null}
      <ul className="m-0 list-none p-0">
        {steps.map((step) => (
          <ChecklistRow
            key={step.key}
            step={step}
            actions={
              <StepActions
                step={step.key}
                lead={step.key === next}
                pending={actions.pending.security}
                onInvite={() => setInviting(true)}
                onRecommended={actions.applyRecommended}
              />
            }
          >
            {step.key === "checks" ? (
              <InlineChecks checks={setup.checks} lead={next === "checks"} pending={actions.pending.checks} onSave={actions.saveChecks} />
            ) : null}
          </ChecklistRow>
        ))}
      </ul>
      {inviting ? (
        <InviteRowsDialog
          onClose={() => setInviting(false)}
          onSent={(count) => {
            setSent(INVITE_ROWS_TEXT.sent(count));
            firstRun.reloadTeam();
          }}
        />
      ) : null}
    </Panel>
  );
}
