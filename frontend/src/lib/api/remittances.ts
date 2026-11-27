import { request, requestFile, type DownloadedFile } from "./client";
import type { AppealDays, AppealDraft, RemittanceDetail, RemittanceFilter, RemittancePage, RemittanceUpload } from "./types";

export function getRemittances(offset: number): Promise<RemittancePage> {
  return request<RemittancePage>("/api/remittances", { query: { offset } });
}

export function getRemittance(remittanceId: string, status: RemittanceFilter): Promise<RemittanceDetail> {
  return request<RemittanceDetail>(`/api/remittances/${encodeURIComponent(remittanceId)}`, { query: { status } });
}

export function uploadRemittance(file: File): Promise<RemittanceUpload> {
  const form = new FormData();
  form.set("file", file, file.name);
  return request<RemittanceUpload>("/api/remittances", { method: "POST", form });
}

export function getAppealDraft(lineId: string): Promise<AppealDraft> {
  return request<AppealDraft>(`/api/remittances/lines/${encodeURIComponent(lineId)}/appeal`);
}

export function downloadDefensePacket(path: string): Promise<DownloadedFile> {
  return requestFile(path);
}

export function getAppealDays(): Promise<AppealDays> {
  return request<AppealDays>("/api/remittances/appeal-days");
}

export function saveAppealDays(days: Partial<AppealDays>): Promise<AppealDays> {
  return request<AppealDays>("/api/remittances/appeal-days", { method: "PUT", body: { days } });
}
