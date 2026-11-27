"use client";

import { useState } from "react";
import type { NoteDetail } from "@/lib/api/types";
import { openQuestions } from "../findings";
import type { ReviewPermissions } from "../permissions";
import type { Neighbours } from "../useNoteData";
import type { ReviewActions } from "../useReviewActions";
import { useReviewShortcuts } from "../useReviewShortcuts";
import { ClaimBar } from "./ClaimBar";
import { NoteHeading } from "./NoteHeading";
import { NoteTools } from "./NoteTools";
import { NotePanel } from "./NotePanel";
import { ReviewDialogs, type OpenDialog } from "./ReviewDialogs";
import { ReviewPanel } from "./ReviewPanel";
import { StatusBanner } from "./StatusBanner";
import { SummaryPanel } from "./SummaryPanel";
import { DayBanner } from "@/components/shared/day-checks/DayBanner";

interface ReviewWorkspaceProps {
  detail: NoteDetail;
  placeLabel: string;
  permissions: ReviewPermissions;
  actions: ReviewActions;
  neighbours: Neighbours;
  onGo: (noteId: string) => void;
  onReplace: (detail: NoteDetail) => void;
  onReload: () => void;
  onApproved: () => void;
}

export function ReviewWorkspace(props: ReviewWorkspaceProps) {
  const { detail, placeLabel, permissions, actions, neighbours, onGo, onReplace, onReload, onApproved } = props;
  const [dialog, setDialog] = useState<OpenDialog>(null);
  const questions = openQuestions(detail.findings);
  const { previous, next } = neighbours;
  const openAsk = permissions.ask ? () => setDialog("ask") : null;

  useReviewShortcuts({
    nextNote: next ? () => onGo(next) : undefined,
    previousNote: previous ? () => onGo(previous) : undefined,
    approve: permissions.approve ? () => void actions.approve() : undefined,
    askProvider: openAsk ?? undefined,
  });

  return (
    <>
      <div className="mx-auto flex w-full max-w-review flex-col gap-6 px-4 pt-8 pb-10 sm:px-8">
        <NoteHeading note={detail.note} placeLabel={placeLabel} />
        <NoteTools
          note={detail.note}
          permissions={permissions}
          onVisitType={(visitType) => void actions.changeVisitType(visitType)}
          onChanged={onReload}
        />
        <StatusBanner
          note={detail.note}
          reason={detail.failure}
          onRetry={permissions.retry ? () => void actions.retry() : null}
          onReopen={permissions.reopen ? () => void actions.reopen() : null}
          retryPending={actions.pending}
        />
        <DayBanner noteId={detail.note.id} />
        <SummaryPanel detail={detail} />
        <div className="flex flex-wrap items-start gap-6">
          <NotePanel texts={detail.texts} findings={detail.findings} />
          <ReviewPanel detail={detail} permissions={permissions} actions={actions} onReplace={onReplace} onAsk={openAsk} />
        </div>
      </div>
      <ClaimBar
        detail={detail}
        permissions={permissions}
        actions={actions}
        questionCount={questions.length}
        onAsk={() => setDialog("ask")}
        onFlag={() => setDialog("flag")}
        onKeep={() => setDialog("keep")}
      />
      <ReviewDialogs
        open={dialog}
        detail={detail}
        questions={questions}
        onClose={() => setDialog(null)}
        onChanged={() => {
          setDialog(null);
          onReload();
        }}
        onApproved={onApproved}
      />
    </>
  );
}
