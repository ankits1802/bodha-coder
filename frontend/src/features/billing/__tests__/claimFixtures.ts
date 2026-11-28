import type { BillingList, BillingRow, ClaimColumn, ClearinghouseSummary } from "@/lib/api/types";

export const SFTP: ClearinghouseSummary = { name: "Office Ally", transport: "sftp", usage: "test" };
export const PORTAL: ClearinghouseSummary = { name: "Availity", transport: "portal", usage: "production" };

export function claimRow(id: string, claim: ClaimColumn | null): BillingRow {
  return {
    id,
    approved_at: "2026-11-26T15:00:00Z",
    approved_by: "Priya Nair",
    changed: 0,
    codes: ["99214", "I10"],
    cpt: ["99214"],
    estimate: 128.4,
    exported_at: null,
    held: false,
    icd10: ["I10"],
    npi: "1234567893",
    patient_name: "Marisol Reyes",
    place_code: "11",
    provider_name: "Elena Varga",
    service_date: "2026-11-25",
    snapshot_id: `snapshot-${id}`,
    snapshot_revision: 1,
    claim,
  };
}

export function billingWith(items: BillingRow[], clearinghouse: ClearinghouseSummary | null): BillingList {
  return {
    items,
    clearinghouse,
    limit: 500,
    offset: 0,
    page_size: 100,
    summary: { exported_today: 0, held_for_provider: 0, ready: items.length },
    total: items.length,
  };
}
