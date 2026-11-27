import { request, requestFile, type DownloadedFile } from "./client";
import type { BillingList, BillingShow, ExportPage, InsightDays, Insights } from "./types";

export function getBilling(show: BillingShow, offset: number): Promise<BillingList> {
  return request<BillingList>("/api/billing", { query: { show, offset } });
}

export function exportClaims(noteIds: string[] | null, again = false): Promise<DownloadedFile> {
  return requestFile("/api/billing/export", { method: "POST", body: { note_ids: noteIds, again } });
}

export function getInsights(days: InsightDays): Promise<Insights> {
  return request<Insights>("/api/insights", { query: { days } });
}

export function getExports(offset: number): Promise<ExportPage> {
  return request<ExportPage>("/api/billing/exports", { query: { offset } });
}

export function downloadExport(exportId: string): Promise<DownloadedFile> {
  return requestFile(`/api/billing/exports/${encodeURIComponent(exportId)}/file`);
}

export function downloadClaimLines(): Promise<DownloadedFile> {
  return requestFile("/api/billing/claim-lines", { method: "POST", body: { format: "csv" } });
}
