import { StatusDot } from "@/components/ui/StatusDot";
import { TextButton } from "@/components/ui/TextButton";
import type { BillingRow } from "@/lib/api/types";
import { CLAIM_TONES, claimNote, offersDetails } from "../claimStatus";
import { CLAIM_TEXT } from "../strings";

interface ClaimCellProps {
  row: BillingRow;
  onDetails: (row: BillingRow) => void;
}

export function ClaimCell({ row, onDetails }: ClaimCellProps) {
  const claim = row.claim;
  if (claim === null) return null;
  const note = claimNote(claim);
  return (
    <span className="flex flex-col items-start gap-1">
      <StatusDot tone={CLAIM_TONES[claim.status]}>{CLAIM_TEXT.statuses[claim.status]}</StatusDot>
      {note ? <span className="max-w-64 text-footnote text-secondary">{note}</span> : null}
      {offersDetails(claim) ? (
        <TextButton className="text-footnote" aria-label={CLAIM_TEXT.detailsFor(row.patient_name ?? row.id)} onClick={() => onDetails(row)}>
          {CLAIM_TEXT.details}
        </TextButton>
      ) : null}
    </span>
  );
}
