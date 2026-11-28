import type { StatusTone } from "@/components/ui/StatusDot";
import { sentence } from "@/lib/api/errors";
import type { BillingRow, ClaimColumn, ClaimStatus } from "@/lib/api/types";
import { CLAIM_TEXT } from "./strings";

const CHARGE_PREFIX = "charge:";
const SHOWN_MISSING = 3;
const DETAIL_STATUSES: readonly ClaimStatus[] = ["missing", "ready", "rejected", "failed"];

export const CLAIM_TONES: Record<ClaimStatus, StatusTone> = {
  missing: "warn",
  ready: "neutral",
  sending: "low",
  sent: "low",
  accepted: "ok",
  rejected: "bad",
  failed: "bad",
};

export function missingLabel(key: string): string {
  if (key.startsWith(CHARGE_PREFIX)) return CLAIM_TEXT.charge(key.slice(CHARGE_PREFIX.length));
  return CLAIM_TEXT.missing[key] ?? key;
}

export function missingSummary(missing: readonly string[]): string {
  const shown = missing.slice(0, SHOWN_MISSING).map(missingLabel);
  const rest = missing.length - shown.length;
  return rest > 0 ? `${shown.join(", ")} ${CLAIM_TEXT.more(rest)}` : shown.join(", ");
}

export function claimNote(claim: ClaimColumn): string | null {
  if (claim.status === "missing") return missingSummary(claim.missing);
  const reason = claim.reasons[0]?.text;
  if (claim.status === "rejected" || claim.status === "failed") return reason ? sentence(reason) : null;
  return null;
}

export function offersDetails(claim: ClaimColumn | null): boolean {
  return claim !== null && DETAIL_STATUSES.includes(claim.status);
}

export function isSendable(row: BillingRow): boolean {
  const claim = row.claim;
  if (row.held || claim === null || claim.missing.length > 0) return false;
  return claim.status === "ready" || claim.status === "rejected" || claim.status === "failed";
}

export function sendableIds(rows: readonly BillingRow[]): string[] {
  return rows.filter(isSendable).map((row) => row.id);
}
