import { CodeChip } from "@/components/ui/CodeChip";
import type { ClaimEstimates } from "@/lib/api/types";
import { formatMoney, formatMoneyChange } from "@/lib/format";
import { REVIEW_TEXT } from "../strings";

const WORDS = REVIEW_TEXT.estimate;

interface ClaimCodesProps {
  claim: string[];
  estimate: ClaimEstimates | null;
}

export function ClaimCodes({ claim, estimate }: ClaimCodesProps) {
  const amounts = new Map((estimate?.claim.lines ?? []).map((line) => [line.code, line.amount]));
  return (
    <span className="inline-flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
      {claim.map((code) => (
        <span key={code} className="inline-flex items-center gap-1.25">
          <CodeChip code={code} />
          {amounts.has(code) ? (
            <span className="text-footnote text-secondary tabular-nums">{WORDS.line(formatMoney(amounts.get(code) ?? null))}</span>
          ) : null}
        </span>
      ))}
    </span>
  );
}

export function EstimateSummary({ estimate }: { estimate: ClaimEstimates }) {
  return (
    <p className="m-0 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-footnote text-secondary tabular-nums">
      <span className="font-medium text-label-soft">{WORDS.label}</span>
      <span>{WORDS.billed(formatMoney(estimate.billed.total))}</span>
      <span>{WORDS.claim(formatMoney(estimate.claim.total))}</span>
      <span>{WORDS.difference(formatMoneyChange(estimate.difference))}</span>
    </p>
  );
}
