"use client";

import { useState, type ReactNode } from "react";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel } from "@/components/ui/Panel";
import { useAction } from "@/hooks/useAction";
import { useQueryParams } from "@/hooks/useQueryParams";
import { saveDecisions } from "@/lib/api/notes";
import type { Choice, Finding, NoteDetail } from "@/lib/api/types";
import { riskSummary } from "../findings";
import type { ReviewPermissions } from "../permissions";
import { REVIEW_TEXT } from "../strings";
import type { ReviewActions } from "../useReviewActions";
import { AuditTab } from "./AuditTab";
import { CodesTab } from "./CodesTab";
import { HistoryTab } from "./HistoryTab";
import { QuestionsTab } from "./QuestionsTab";
import { RiskAdjustmentTab } from "./RiskAdjustmentTab";
import { Tabs, type TabItem } from "./Tabs";
import { WordingTab } from "./WordingTab";

export type ReviewTab = "codes" | "questions" | "wording" | "audit" | "risk" | "history";

const TAB_ORDER: ReviewTab[] = ["codes", "questions", "wording", "audit", "risk", "history"];

function tabsFor(detail: NoteDetail): TabItem<ReviewTab>[] {
  const shown = TAB_ORDER.filter((value) => value !== "risk" || riskSummary(detail.findings) !== null);
  return shown.map((value) => ({ value, label: REVIEW_TEXT.tabs[value] }));
}

function parseTab(value: string | null, tabs: TabItem<ReviewTab>[]): ReviewTab {
  return tabs.find((tab) => tab.value === value)?.value ?? "codes";
}

interface ReviewPanelProps {
  detail: NoteDetail;
  permissions: ReviewPermissions;
  actions: ReviewActions;
  onReplace: (detail: NoteDetail) => void;
  onAsk: (() => void) | null;
}

export function ReviewPanel({ detail, permissions, actions, onReplace, onAsk }: ReviewPanelProps) {
  const query = useQueryParams();
  const tabs = tabsFor(detail);
  const tab = parseTab(query.get("tab"), tabs);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [reminded, setReminded] = useState(false);
  const decide = useAction((key: string, choice: Choice) => saveDecisions(detail.note.id, { [key]: choice }));

  async function choose(finding: Finding, choice: Choice): Promise<void> {
    setBusyKey(finding.key);
    const outcome = await decide.run(finding.key, choice);
    setBusyKey(null);
    if (outcome.ok) onReplace(outcome.value);
  }

  async function remind(): Promise<void> {
    setReminded((await actions.remind()).ok);
  }

  const decision = { editable: permissions.decide, busyKey, onChoose: (finding: Finding, choice: Choice) => void choose(finding, choice) };
  const panels: Record<ReviewTab, ReactNode> = {
    codes: <CodesTab detail={detail} {...decision} onSaved={onReplace} />,
    questions: (
      <QuestionsTab
        detail={detail}
        {...decision}
        onAsk={onAsk}
        onRemind={permissions.remind ? () => void remind() : null}
        remindPending={actions.remindPending}
        onCancel={permissions.cancelRequest ? () => void actions.cancelRequest() : null}
        cancelPending={actions.cancelPending}
        remindMessage={actions.remindError ?? (reminded ? REVIEW_TEXT.questions.reminded : null)}
      />
    ),
    wording: <WordingTab detail={detail} />,
    audit: <AuditTab detail={detail} />,
    risk: <RiskAdjustmentTab detail={detail} {...decision} />,
    history: <HistoryTab detail={detail} />,
  };

  return (
    <Panel aria-label={REVIEW_TEXT.reviewLabel} className="min-w-0 flex-[1_1_34rem]">
      <Tabs
        label={REVIEW_TEXT.reviewLabel}
        tabs={tabs}
        value={tab}
        onChange={(next) => query.update({ tab: next === "codes" ? null : next })}
        headerClassName="border-b border-hairline px-5 py-3.5"
      >
        {decide.error ? (
          <div className="px-5 pt-4">
            <InlineAlert tone="bad">{decide.error}</InlineAlert>
          </div>
        ) : null}
        {panels[tab]}
      </Tabs>
    </Panel>
  );
}
