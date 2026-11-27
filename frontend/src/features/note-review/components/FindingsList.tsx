"use client";

import { useId, type FocusEvent, type ReactNode } from "react";
import { ClaimChecksPanel } from "@/components/shared/claim-checks/ClaimChecksPanel";
import { ARROW_REGION } from "@/components/shared/shortcuts/registry";
import type { NoteDetail } from "@/lib/api/types";
import { quoteCheck, riskSummary } from "../findings";
import { GROUP_ORDER, groupRows, showsSupported, type ReviewFilter, type ReviewGroupKey, type ReviewGroups, type ReviewRow } from "../reviewList";
import { REVIEW_TEXT } from "../strings";
import { FINDING_KEY_ATTRIBUTE } from "../useFindingFocus";
import { DecidableRow, type DecisionProps } from "./DecidableRow";
import { GuidanceRow, WordingBlock } from "./GuidanceRows";
import { GuidanceSections, hasGuidance } from "./GuidanceSections";
import { QuestionTools, hasQuestionTools, type QuestionToolsProps } from "./QuestionTools";
import { RiskSummarySection } from "./RiskSummarySection";

interface FindingsListProps {
  detail: NoteDetail;
  groups: ReviewGroups;
  filter: ReviewFilter;
  decision: DecisionProps;
  questions: QuestionToolsProps;
  supported: ReactNode;
  onFocusFinding: (key: string) => void;
}

interface Extras {
  before: ReactNode;
  after: ReactNode;
}

const GUIDANCE_KINDS: readonly string[] = ["audit_risk", "audit_finding", "cdi_gap"];
const NO_EXTRAS: Extras = { before: null, after: null };

function shows(filter: ReviewFilter, group: ReviewGroupKey): boolean {
  return filter === "all" || filter === group;
}

function extrasFor(group: ReviewGroupKey, filter: ReviewFilter, props: FindingsListProps): Extras {
  const { detail, questions } = props;
  if (!shows(filter, group)) return NO_EXTRAS;
  const summary = group === "risk" ? riskSummary(detail.findings) : null;
  if (summary) return { before: <RiskSummarySection summary={summary} />, after: null };
  if (group === "changes" && detail.analysis) return { before: null, after: <ClaimChecksPanel noteId={detail.note.id} claim={detail.claim} /> };
  if (group === "questions" && hasQuestionTools(detail, questions)) return { before: null, after: <QuestionTools detail={detail} tools={questions} /> };
  if (group === "guidance" && hasGuidance(detail)) return { before: null, after: <GuidanceSections detail={detail} /> };
  return NO_EXTRAS;
}

function Row({ row, decision, detail }: { row: ReviewRow; decision: DecisionProps; detail: NoteDetail }) {
  if (GUIDANCE_KINDS.includes(row.finding.kind)) return <GuidanceRow finding={row.finding} />;
  return (
    <DecidableRow finding={row.finding} decision={decision} quote={quoteCheck(row.finding, detail.texts)}>
      {row.wording.map((gap) => (
        <WordingBlock key={gap.key} gap={gap} />
      ))}
    </DecidableRow>
  );
}

function Group({ group, rows, extras, children }: { group: ReviewGroupKey; rows: ReviewRow[]; extras: Extras; children: ReactNode }) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="border-t border-hairline first:border-t-0">
      <h3 id={headingId} className="m-0 px-5 pt-4 pb-1 font-sans text-subhead font-semibold text-secondary">
        {REVIEW_TEXT.groups[group]}
      </h3>
      {extras.before}
      {rows.length > 0 ? <ul className="m-0 list-none p-0">{children}</ul> : null}
      {extras.after}
    </section>
  );
}

export function FindingsList(props: FindingsListProps) {
  const { detail, groups, filter, decision, supported, onFocusFinding } = props;
  const sections = GROUP_ORDER.map((group) => ({ group, rows: groupRows(groups, group, filter), extras: extrasFor(group, filter, props) })).filter(
    (section) => section.rows.length > 0 || section.extras.before !== null || section.extras.after !== null,
  );
  const withSupported = showsSupported(filter) && groups.supported.length > 0;

  function onFocus(event: FocusEvent<HTMLDivElement>): void {
    const key = (event.target as HTMLElement).closest(`[${FINDING_KEY_ATTRIBUTE}]`)?.getAttribute(FINDING_KEY_ATTRIBUTE);
    if (key) onFocusFinding(key);
  }

  return (
    <div {...{ [ARROW_REGION]: "" }} onFocus={onFocus}>
      {sections.map(({ group, rows, extras }) => (
        <Group key={group} group={group} rows={rows} extras={extras}>
          {rows.map((row) => (
            <Row key={row.finding.key} row={row} decision={decision} detail={detail} />
          ))}
        </Group>
      ))}
      {withSupported ? supported : null}
      {sections.length === 0 && !withSupported ? <p className="m-0 px-5 py-6 text-secondary">{REVIEW_TEXT.nothingHere}</p> : null}
    </div>
  );
}
