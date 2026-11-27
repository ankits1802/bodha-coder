"use client";

import { useState } from "react";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel } from "@/components/ui/Panel";
import { useQueryParams } from "@/hooks/useQueryParams";
import type { Choice, Finding, NoteDetail } from "@/lib/api/types";
import { decisionOrder } from "../decisionFlow";
import { codeLabel, latestBilled } from "../findings";
import { departsWith } from "../overrideReasons";
import type { ReviewPermissions } from "../permissions";
import { filterCounts, reviewGroups, supportedToAccept, visibleRows } from "../reviewList";
import { filterChanges, historyChanges, reviewView } from "../reviewView";
import { REVIEW_TEXT } from "../strings";
import { ALL_KEYS, type Decisions } from "../useDecisions";
import { useFindingFocus } from "../useFindingFocus";
import { useFindingKeys } from "../useFindingKeys";
import type { OverridePrompt } from "../useOverridePrompt";
import type { ReviewActions } from "../useReviewActions";
import { BilledCodesEditor } from "./BilledCodesEditor";
import type { DecisionProps } from "./DecidableRow";
import { FindingsList } from "./FindingsList";
import { HistoryDrawer } from "./HistoryDrawer";
import { ReviewFilterBar } from "./ReviewFilterBar";
import { SupportedGroup } from "./SupportedGroup";

interface ReviewPanelProps {
  detail: NoteDetail;
  permissions: ReviewPermissions;
  actions: ReviewActions;
  decisions: Decisions;
  prompt: OverridePrompt;
  onReplace: (detail: NoteDetail) => void;
  onAsk: (() => void) | null;
}

export function ReviewPanel({ detail, permissions, actions, decisions, prompt, onReplace, onAsk }: ReviewPanelProps) {
  const query = useQueryParams();
  const view = reviewView({ filter: query.get("filter"), tab: query.get("tab"), history: query.get("history") });
  const [reminded, setReminded] = useState(false);
  const [editingCodes, setEditingCodes] = useState(false);
  const [supportedOpen, setSupportedOpen] = useState(false);
  const groups = reviewGroups(detail);
  const focus = useFindingFocus(decisionOrder(visibleRows(groups, view.filter)));
  const toAccept = permissions.decide ? supportedToAccept(groups) : [];
  useFindingKeys({ detail, permissions, focus, prompt, decisions, toAccept, onEditCodes: () => setEditingCodes(true) });

  async function remind(): Promise<void> {
    setReminded((await actions.remind()).ok);
  }

  const decision: DecisionProps = {
    editable: permissions.decide,
    savingKey: decisions.savingKey,
    currentKey: focus.currentKey,
    onChoose: prompt.request,
    onPicked: (finding: Finding, choice: Choice) => {
      if (!departsWith(finding, choice)) focus.moveAfter(finding.key);
    },
    prompt: {
      ...prompt,
      confirm: (override) => {
        const finding = prompt.pending?.finding;
        prompt.confirm(override);
        if (finding) focus.moveAfter(finding.key);
      },
    },
  };
  const questions = {
    onAsk,
    onRemind: permissions.remind ? () => void remind() : null,
    remindPending: actions.remindPending,
    onCancel: permissions.cancelRequest ? () => void actions.cancelRequest() : null,
    cancelPending: actions.cancelPending,
    remindMessage: actions.remindError ?? (reminded ? REVIEW_TEXT.questions.reminded : null),
  };
  const supported = (
    <SupportedGroup
      findings={groups.supported}
      texts={detail.texts}
      open={supportedOpen}
      onToggle={() => setSupportedOpen(!supportedOpen)}
      onAcceptAll={toAccept.length > 0 ? () => decisions.acceptAll(toAccept) : null}
      pending={decisions.savingKey === ALL_KEYS}
    />
  );

  return (
    <Panel aria-label={REVIEW_TEXT.reviewLabel} className="min-w-0 flex-[1_1_34rem]">
      <ReviewFilterBar
        filter={view.filter}
        counts={filterCounts(groups)}
        onFilter={(filter) => query.update(filterChanges(view, filter))}
        onHistory={() => query.update(historyChanges(view, true))}
      />
      {decisions.error ? (
        <div className="px-5 pt-4">
          <InlineAlert tone="bad">{decisions.error}</InlineAlert>
        </div>
      ) : null}
      <FindingsList
        detail={detail}
        groups={groups}
        filter={view.filter}
        decision={decision}
        questions={questions}
        supported={supported}
        onFocusFinding={focus.focusIn}
      />
      <BilledCodesEditor
        noteId={detail.note.id}
        codes={latestBilled(detail.history).map(codeLabel)}
        editable={permissions.decide}
        editing={editingCodes}
        onEditing={setEditingCodes}
        onSaved={onReplace}
      />
      <HistoryDrawer open={view.history} detail={detail} onClose={() => query.update(historyChanges(view, false))} />
    </Panel>
  );
}
