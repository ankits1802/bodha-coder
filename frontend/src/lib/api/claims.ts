import { request, requestFile, type DownloadedFile } from "./client";
import type { AckUpload, ClaimDetailsInput, ClaimDetailsView, ClaimFilePage, ClaimSent } from "./types";

const SUBMISSIONS = "/api/billing/claim-submissions";

function claimDetailsPath(noteId: string): string {
  return `/api/notes/${encodeURIComponent(noteId)}/claim-details`;
}

export function sendClaims(noteIds: string[] | null): Promise<ClaimSent> {
  return request<ClaimSent>(SUBMISSIONS, { method: "POST", body: noteIds ? { note_ids: noteIds } : {} });
}

export function downloadClaimFile(noteIds: string[] | null): Promise<DownloadedFile> {
  return requestFile("/api/billing/claim-file", { method: "POST", body: noteIds ? { note_ids: noteIds } : {} });
}

export function getClaimFiles(offset: number): Promise<ClaimFilePage> {
  return request<ClaimFilePage>(SUBMISSIONS, { query: { offset } });
}

export function downloadStoredClaimFile(submissionId: string): Promise<DownloadedFile> {
  return requestFile(`${SUBMISSIONS}/${encodeURIComponent(submissionId)}/file`);
}

export function uploadAcknowledgment(file: File): Promise<AckUpload> {
  const form = new FormData();
  form.set("file", file, file.name);
  return request<AckUpload>("/api/billing/acknowledgments", { method: "POST", form });
}

export function getClaimDetails(noteId: string): Promise<ClaimDetailsView> {
  return request<ClaimDetailsView>(claimDetailsPath(noteId));
}

export function saveClaimDetails(noteId: string, details: ClaimDetailsInput): Promise<ClaimDetailsView> {
  return request<ClaimDetailsView>(claimDetailsPath(noteId), { method: "PUT", body: details });
}
