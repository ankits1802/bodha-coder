import type { Choice, Finding, NoteDetail } from "@/lib/api/types";
import { riskSummary, suspectedConditions } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { DecisionControl } from "./DecisionControl";
import { FindingRow } from "./FindingRow";
import { RiskCategories, RiskScores } from "./RiskAdjustmentCategories";
import { TabSection } from "./TabSection";

interface RiskAdjustmentTabProps {
  detail: NoteDetail;
  editable: boolean;
  busyKey: string | null;
  onChoose: (finding: Finding, choice: Choice) => void;
}

export function RiskAdjustmentTab({ detail, editable, busyKey, onChoose }: RiskAdjustmentTabProps) {
  const words = REVIEW_TEXT.risk;
  const summary = riskSummary(detail.findings);
  const suspected = suspectedConditions(detail.findings);
  if (!summary) return <p className="m-0 px-5 py-6 text-secondary">{words.none}</p>;
  if (!summary.available) return <p className="m-0 px-5 py-6 text-secondary">{words.unavailable(summary.paymentYear)}</p>;
  return (
    <>
      <RiskScores summary={summary} />
      <RiskCategories categories={summary.categories} />
      {suspected.length > 0 ? (
        <TabSection title={words.suspected}>
          <ul className="-mx-5 my-0 list-none p-0">
            {suspected.map((finding) => (
              <FindingRow
                key={finding.key}
                finding={finding}
                decision={<DecisionControl finding={finding} editable={editable} busy={busyKey === finding.key} onChoose={onChoose} />}
              />
            ))}
          </ul>
        </TabSection>
      ) : null}
    </>
  );
}
