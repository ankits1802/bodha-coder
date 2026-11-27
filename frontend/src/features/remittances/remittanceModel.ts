import type { StatusTone } from "@/components/ui/StatusDot";
import type { RemittanceCounts, RemittanceFilter, RemittanceLine, RemittanceLineStatus } from "@/lib/api/types";
import { formatMoney } from "@/lib/format";

export const REMITTANCE_FILTERS: readonly RemittanceFilter[] = ["all", "downcoded", "denied", "unmatched"];

export const STATUS_ORDER: readonly RemittanceLineStatus[] = ["downcoded", "denied", "unmatched", "matched", "paid_as_billed"];

export const STATUS_TONES: Record<RemittanceLineStatus, StatusTone> = {
  paid_as_billed: "ok",
  downcoded: "warn",
  denied: "bad",
  matched: "dark",
  unmatched: "neutral",
};

const CENTS_PER_DOLLAR = 100;

export function isRemittanceFilter(value: string | null): value is RemittanceFilter {
  return value !== null && (REMITTANCE_FILTERS as readonly string[]).includes(value);
}

export function formatCents(cents: number | null): string {
  return formatMoney(cents === null ? null : cents / CENTS_PER_DOLLAR);
}

export function canAppeal(line: RemittanceLine): boolean {
  return line.appeal_by !== null;
}

export function countedStatuses(counts: RemittanceCounts): { status: RemittanceLineStatus; count: number }[] {
  return STATUS_ORDER.flatMap((status) => {
    const count = counts[status] ?? 0;
    return count > 0 ? [{ status, count }] : [];
  });
}
