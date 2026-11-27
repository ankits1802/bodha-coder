"use client";

import { useState, type ReactNode } from "react";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel } from "@/components/ui/Panel";
import { useShortcuts } from "@/components/shared/shortcuts/useShortcuts";
import { useQueryParams } from "@/hooks/useQueryParams";
import type { Choice, Finding, NoteDetail } from "@/lib/api/types";
import { choiceFor, decisionOrder } from "../decisionFlow";
import { riskSummary } from "../findings";
import { departsWith } from "../overrideReasons";
import type { ReviewPermissions } from "../permissions";
import { REVIEW_TEXT } from "../strings";
import type { Decisions } from "../useDecisions";
import { useFindingFocus } from "../useFindingFocus";
import type { OverridePrompt } from "../useOverridePrompt";
import type { ReviewActions } from "../useReviewActions";
import { AuditTab } from "./AuditTab";
import { CodesTab } from "./CodesTab";
import type { DecisionProps } from "./DecidableRow";
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
  decisions: Decisions;
  prompt: OverridePrompt;
  onReplace: (detail: NoteDetail) => void;
  onAsk: (() => void) | null;
}

export function ReviewPanel({ detail, permissions, actions, decisions, prompt, onReplace, onAsk }: ReviewPanelProps) {
  const query = useQueryParams();
  const tabs = tabsFor(detail);
  const tab = parseTab(query.get("tab"), tabs);
  const [reminded, setReminded] = useState(false);
  const order = decisionOrder(detail.findings, tab);
  const focus = useFindingFocus(order, tab);

  function decideCurrent(accept: boolean): void {
    const finding = detail.findings.find((item) => item.key === focus.currentKey);
    const choice = finding ? choiceFor(finding, accept) : null;
    if (!finding || !choice) return;
    prompt.request(finding, choice);
    if (!departsWith(finding, choice)) focus.moveAfter(finding.key);
  }

  const deciding = permissions.decide && focus.currentKey !== null && prompt.pending === null;
  useShortcuts("review", {
    acceptFinding: deciding ? () => decideCurrent(true) : undefined,
    rejectFinding: deciding ? () => decideCurrent(false) : undefined,
  });

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
  const panels: Record<ReviewTab, ReactNode> = {
    codes: <CodesTab detail={detail} decision={decision} onSaved={onReplace} />,
    questions: (
      <QuestionsTab
        detail={detail}
        decision={decision}
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
    risk: <RiskAdjustmentTab detail={detail} decision={decision} />,
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
        {decisions.error ? (
          <div className="px-5 pt-4">
            <InlineAlert tone="bad">{decisions.error}</InlineAlert>
          </div>
        ) : null}
        {panels[tab]}
      </Tabs>
    </Panel>
  );
}
