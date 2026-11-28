"use client";

import { Dialog } from "@/components/ui/Dialog";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { useRemote } from "@/hooks/useRemote";
import { getClaimDetails } from "@/lib/api/claims";
import { getPayers } from "@/lib/api/notes";
import type { BillingRow } from "@/lib/api/types";
import { CLAIM_DETAILS_TEXT } from "../strings";
import { ClaimDetailsForm } from "./ClaimDetailsForm";

interface ClaimDetailsDialogProps {
  row: BillingRow;
  onClose: () => void;
  onSaved: () => void;
}

export function ClaimDetailsDialog({ row, onClose, onSaved }: ClaimDetailsDialogProps) {
  const details = useRemote(`claim-details:${row.id}`, () => getClaimDetails(row.id));
  const payers = useRemote("billing-payers", getPayers);
  const words = CLAIM_DETAILS_TEXT;

  if (details.state.status === "success" && payers.state.status === "success") {
    return <ClaimDetailsForm row={row} view={details.state.data} payers={payers.state.data} onClose={onClose} onSaved={onSaved} />;
  }
  const failed = details.state.status === "error" ? details.state.error : payers.state.status === "error" ? payers.state.error : null;
  return (
    <Dialog open onClose={onClose} title={words.title}>
      {failed ? (
        <ErrorState
          message={failed}
          retryLabel={words.retry}
          onRetry={() => {
            details.reload();
            payers.reload();
          }}
        />
      ) : (
        <LoadingState label={words.loading} />
      )}
    </Dialog>
  );
}
