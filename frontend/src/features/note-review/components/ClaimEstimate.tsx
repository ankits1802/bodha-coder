import { CodeChip } from "@/components/ui/CodeChip";
import type { ClaimEstimates, ClaimPointers, PointerLine } from "@/lib/api/types";
import { formatMoney, formatMoneyChange } from "@/lib/format";
import { REVIEW_TEXT } from "../strings";

const WORDS = REVIEW_TEXT.estimate;

interface ClaimCodesProps {
  claim: string[];
  estimate: ClaimEstimates | null;
  pointers?: ClaimPointers | null;
  onEdit?: ((line: PointerLine) => void) | null;
}

interface ClaimCodeProps {
  code: string;
  line: PointerLine | null;
  letters: Map<string, string | null>;
  onEdit: ((line: PointerLine) => void) | null;
}

function Letters({ value }: { value: string }) {
  return value ? <span className="text-caption text-secondary tabular-nums">{value}</span> : null;
}

function ClaimCode({ code, line, letters, onEdit }: ClaimCodeProps) {
  if (!line) {
    return (
      <>
        <Letters value={letters.get(code) ?? ""} />
        <CodeChip code={code} />
      </>
    );
  }
  const pointed = line.pointers.map((pointer) => letters.get(pointer) ?? "").join("");
  if (!onEdit) {
    return (
      <>
        <CodeChip code={code} />
        <Letters value={pointed} />
      </>
    );
  }
  return (
    <button
      type="button"
      aria-haspopup="dialog"
      aria-label={REVIEW_TEXT.pointers.line(code, pointed, line.pointers.join(", "))}
      onClick={() => onEdit(line)}
      className="inline-flex cursor-pointer items-center gap-1.25 rounded-chip"
    >
      <CodeChip code={code} />{" "}
      <Letters value={pointed} />
    </button>
  );
}

export function ClaimCodes({ claim, estimate, pointers = null, onEdit = null }: ClaimCodesProps) {
  const amounts = new Map((estimate?.claim.lines ?? []).map((line) => [line.code, line.amount]));
  const lines = new Map((pointers?.lines ?? []).map((line) => [line.label, line]));
  const letters = new Map((pointers?.diagnoses ?? []).map((diagnosis) => [diagnosis.code, diagnosis.letter]));
  return (
    <span className="inline-flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
      {claim.map((code) => (
        <span key={code} className="inline-flex items-center gap-1.25">
          <ClaimCode code={code} line={lines.get(code) ?? null} letters={letters} onEdit={onEdit} />
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
