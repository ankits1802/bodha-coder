import { isPdf } from "@/components/shared/upload-drop/droppedFiles";
import { buildUploadForm } from "@/lib/api/uploads";
import type { FileDetail, FilePreview, PayerOption, Place, Provider } from "@/lib/api/types";
import { isIsoDate } from "@/lib/dates";
import { parseCodeList } from "@/lib/validation";
import { previewPayer, providerPayer, type PayerSource } from "./uploadPayers";

export { isPdf };

export interface UploadEntry {
  id: string;
  file: File;
  patientName: string | null;
  billed: string | null;
  visitType: string | null;
  providerId: string;
  serviceDate: string;
  placeCode: string;
  payerId: string;
  payerSource: PayerSource | null;
  suggestedPayer: string | null;
  check: boolean;
  confidence: number | null;
  serverDuplicate: boolean;
  duplicate: boolean;
  keep: boolean;
}

export type Placement = Pick<UploadEntry, "providerId" | "serviceDate" | "placeCode">;
export type EntryEdit = Partial<Pick<UploadEntry, "billed" | "visitType" | "keep">>;
export type EntryStatus = "ready" | "check" | "fix" | "duplicate" | "uploaded" | "noCodes";

export interface References {
  providers: Provider[];
  places: Place[];
  payers: PayerOption[];
}

const LEFT_OUT: readonly EntryStatus[] = ["duplicate", "uploaded"];

export function newEntry(file: File, id: string): UploadEntry {
  return {
    id,
    file,
    patientName: null,
    billed: null,
    visitType: null,
    providerId: "",
    serviceDate: "",
    placeCode: "",
    payerId: "",
    payerSource: null,
    suggestedPayer: null,
    check: false,
    confidence: null,
    serverDuplicate: false,
    duplicate: false,
    keep: false,
  };
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

export function applyPreview(entries: UploadEntry[], ids: string[], previews: FilePreview[], references: References): UploadEntry[] {
  const byId = new Map(ids.map((id, index) => [id, previews[index]]));
  return entries.map((entry) => {
    const preview = byId.get(entry.id);
    if (!preview) return entry;
    const providerId = entry.providerId || (preview.provider_id ?? "");
    return {
      ...entry,
      ...previewPayer(entry, preview, providerId, references),
      patientName: entry.patientName ?? preview.patient_name,
      billed: entry.billed ?? preview.cpt,
      providerId,
      serviceDate: entry.serviceDate || (preview.service_date ?? ""),
      placeCode: entry.placeCode || (preview.place_code ?? ""),
      check: preview.check,
      confidence: preview.overall,
      serverDuplicate: preview.duplicate,
    };
  });
}

export function usualPlace(providerId: string, references: References): string | null {
  const provider = references.providers.find((item) => item.id === providerId);
  const code = provider?.place_code ?? null;
  return code && references.places.some((place) => place.code === code) ? code : null;
}

export function placed(entry: UploadEntry, change: Partial<Placement>, references: References): UploadEntry {
  const next = { ...entry, ...change, check: false };
  if (change.providerId === undefined) return next;
  const payer = providerPayer(entry, change.providerId, references);
  if (change.placeCode !== undefined) return { ...next, ...payer };
  return { ...next, ...payer, placeCode: usualPlace(change.providerId, references) ?? entry.placeCode };
}

export function hasPlacement(entry: UploadEntry): boolean {
  return Boolean(entry.providerId && entry.placeCode) && isIsoDate(entry.serviceDate);
}

export function invalidCodes(entry: UploadEntry): string[] {
  return parseCodeList(entry.billed ?? "").invalid;
}

export function entryStatus(entry: UploadEntry): EntryStatus {
  if (entry.duplicate && !entry.keep) return "duplicate";
  if (entry.serverDuplicate) return "uploaded";
  const parsed = parseCodeList(entry.billed ?? "");
  if (parsed.invalid.length > 0) return "fix";
  if (entry.check || !hasPlacement(entry)) return "check";
  return parsed.codes.length > 0 ? "ready" : "noCodes";
}

export function includedEntries(entries: UploadEntry[]): UploadEntry[] {
  return entries.filter((entry) => !LEFT_OUT.includes(entryStatus(entry)));
}

export function uploadDetails(entries: UploadEntry[]): FileDetail[] {
  return includedEntries(entries).map((entry) => ({
    billed: entry.billed === null ? null : entry.billed.trim(),
    visit_type: entry.visitType,
    provider_id: entry.providerId,
    service_date: entry.serviceDate,
    place_code: entry.placeCode,
    payer: entry.payerId || null,
  }));
}

export function canStartUpload(entries: UploadEntry[]): boolean {
  const included = includedEntries(entries);
  return included.length > 0 && included.every((entry) => hasPlacement(entry) && entryStatus(entry) !== "fix");
}

export function makeUploadForm(visitType: string, entries: UploadEntry[]): FormData {
  const included = includedEntries(entries);
  return buildUploadForm(visitType, included.map((entry) => entry.file), uploadDetails(entries));
}

export function countByStatus(entries: UploadEntry[]): Record<EntryStatus, number> {
  const counts: Record<EntryStatus, number> = { ready: 0, check: 0, fix: 0, duplicate: 0, uploaded: 0, noCodes: 0 };
  for (const entry of entries) counts[entryStatus(entry)] += 1;
  return counts;
}

export function sharedValue(entries: UploadEntry[], key: keyof Placement): string {
  const values = new Set(includedEntries(entries).map((entry) => entry[key]));
  const [only] = values;
  return values.size === 1 && only ? only : "";
}
