import type { NoteDetail } from "@/lib/api/types";
import { riskSummary, suspectedConditions } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { DecidableRow, type DecisionProps } from "./DecidableRow";
import { RiskCategories, RiskScores } from "./RiskAdjustmentCategories";
import { TabSection } from "./TabSection";

interface RiskAdjustmentTabProps {
  detail: NoteDetail;
  decision: DecisionProps;
}

export function RiskAdjustmentTab({ detail, decision }: RiskAdjustmentTabProps) {
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
              <DecidableRow key={finding.key} finding={finding} decision={decision} />
            ))}
          </ul>
        </TabSection>
      ) : null}
    </>
  );
}
