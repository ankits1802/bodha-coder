import { CodeChip } from "@/components/ui/CodeChip";
import { StatusDot } from "@/components/ui/StatusDot";
import { claimCodes, openCount, type Decisions } from "./claim";
import styles from "./sample.module.css";
import type { ClaimCodes, SampleNote } from "./samples";
import { SAMPLE_TEXT } from "./strings";

function Chips({ label, codes, billed }: { label: string; codes: readonly string[]; billed: readonly string[] | null }) {
  return (
    <span className="flex flex-wrap items-center gap-1.5">
      <span className="sr-only">{label}</span>
      {codes.map((code, index) => {
        const changed = billed !== null && !billed.includes(code);
        return <CodeChip key={`${index}-${code}`} code={code} variant={changed ? "new" : "default"} className={changed ? styles.swap : ""} />;
      })}
    </span>
  );
}

interface CodeLineProps {
  label: string;
  codes: ClaimCodes;
  billed?: ClaimCodes;
}

export function CodeLine({ label, codes, billed }: CodeLineProps) {
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2">
      <span className="w-12 flex-none text-footnote font-semibold text-secondary">{label}</span>
      <Chips label={SAMPLE_TEXT.procedures} codes={codes.procedures} billed={billed?.procedures ?? null} />
      <span aria-hidden="true" className="h-4 w-px bg-separator" />
      <Chips label={SAMPLE_TEXT.diagnoses} codes={codes.diagnoses} billed={billed?.diagnoses ?? null} />
    </div>
  );
}

export function ClaimSummary({ sample, decisions }: { sample: SampleNote; decisions: Decisions }) {
  const open = openCount(sample.findings, decisions);
  return (
    <div
      role="status"
      aria-label={SAMPLE_TEXT.claim}
      className="mt-auto flex flex-wrap items-center justify-between gap-x-4 gap-y-3 border-t border-hairline bg-footer-panel px-5 py-4 sm:px-6"
    >
      <CodeLine label={SAMPLE_TEXT.claim} codes={claimCodes(sample.billed, sample.findings, decisions)} billed={sample.billed} />
      {open > 0 ? (
        <StatusDot tone="neutral">{SAMPLE_TEXT.toDecide(open)}</StatusDot>
      ) : (
        <StatusDot tone="ok" className={styles.ready}>
          {SAMPLE_TEXT.ready}
        </StatusDot>
      )}
    </div>
  );
}
