import type { RiskSummary } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { RiskCategories, RiskScores } from "./RiskAdjustmentCategories";

export function RiskSummarySection({ summary }: { summary: RiskSummary }) {
  if (!summary.available) return <p className="m-0 px-5 py-4 text-secondary">{REVIEW_TEXT.risk.unavailable(summary.paymentYear)}</p>;
  return (
    <>
      <RiskScores summary={summary} />
      <RiskCategories categories={summary.categories} />
    </>
  );
}
