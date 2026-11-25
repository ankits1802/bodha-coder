import { buildUploadForm } from "@/lib/api/uploads";
import type { FileDetail, FilePreview, UploadPlan } from "@/lib/api/types";
import { isIsoDate } from "@/lib/dates";
import { parseCodeList } from "@/lib/validation";

export interface UploadEntry {
  id: string;
  file: File;
  patientName: string | null;
  billed: string | null;
  visitType: string | null;
  duplicate: boolean;
  keep: boolean;
}

export type EntryStatus = "ready" | "fix" | "duplicate" | "noCodes";

export function isPdf(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

export function newEntry(file: File, id: string): UploadEntry {
  return { id, file, patientName: null, billed: null, visitType: null, duplicate: false, keep: false };
}

export function withDuplicates(entries: UploadEntry[]): UploadEntry[] {
  const seen = new Set<string>();
  return entries.map((entry) => {
    const signature = `${entry.file.name}|${entry.file.size}`;
    const duplicate = seen.has(signature);
    seen.add(signature);
    return duplicate === entry.duplicate ? entry : { ...entry, duplicate, keep: duplicate && entry.keep };
  });
}

export function applyPreview(entries: UploadEntry[], ids: string[], previews: FilePreview[]): UploadEntry[] {
  const byId = new Map(ids.map((id, index) => [id, previews[index]]));
  return entries.map((entry) => {
    const preview = byId.get(entry.id);
    if (!preview) return entry;
    return {
      ...entry,
      patientName: entry.patientName ?? preview.patient_name,
      billed: entry.billed ?? preview.cpt,
    };
  });
}

export function invalidCodes(entry: UploadEntry): string[] {
  return parseCodeList(entry.billed ?? "").invalid;
}

export function entryStatus(entry: UploadEntry): EntryStatus {
  if (entry.duplicate && !entry.keep) return "duplicate";
  const parsed = parseCodeList(entry.billed ?? "");
  if (parsed.invalid.length > 0) return "fix";
  return parsed.codes.length > 0 ? "ready" : "noCodes";
}

export function includedEntries(entries: UploadEntry[]): UploadEntry[] {
  return entries.filter((entry) => entryStatus(entry) !== "duplicate");
}

export function uploadDetails(entries: UploadEntry[]): FileDetail[] {
  return includedEntries(entries).map((entry) => ({
    billed: entry.billed === null ? null : entry.billed.trim(),
    visit_type: entry.visitType,
  }));
}

export function isPlanComplete(plan: UploadPlan): boolean {
  return Boolean(plan.provider_id && plan.place_code && plan.visit_type) && isIsoDate(plan.service_date);
}

export function canStartUpload(plan: UploadPlan, entries: UploadEntry[]): boolean {
  const included = includedEntries(entries);
  return isPlanComplete(plan) && included.length > 0 && included.every((entry) => entryStatus(entry) !== "fix");
}

export function makeUploadForm(plan: UploadPlan, entries: UploadEntry[]): FormData {
  const included = includedEntries(entries);
  return buildUploadForm(plan, included.map((entry) => entry.file), uploadDetails(entries));
}

export function countByStatus(entries: UploadEntry[]): Record<EntryStatus, number> {
  const counts: Record<EntryStatus, number> = { ready: 0, fix: 0, duplicate: 0, noCodes: 0 };
  for (const entry of entries) counts[entryStatus(entry)] += 1;
  return counts;
}

export function suggestedServiceDate(previews: FilePreview[]): string | null {
  return previews.find((preview) => preview.service_date && isIsoDate(preview.service_date))?.service_date ?? null;
}
