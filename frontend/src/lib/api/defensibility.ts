import { request, requestFile, type DownloadedFile } from "./client";
import type { EmMix, FlaggedDays, InsightDays, NoteDay } from "./types";

const notePath = (noteId: string, suffix: string): string => `/api/notes/${encodeURIComponent(noteId)}${suffix}`;

export function downloadDefensePacket(noteId: string): Promise<DownloadedFile> {
  return requestFile(notePath(noteId, "/defense-packet"));
}

export function downloadAuditPackage(noteId: string): Promise<DownloadedFile> {
  return requestFile(notePath(noteId, "/audit-package"), { method: "POST" });
}

export function getNoteDay(noteId: string): Promise<NoteDay> {
  return request<NoteDay>(notePath(noteId, "/day"));
}

export function getFlaggedDays(from: string, to: string): Promise<FlaggedDays> {
  return request<FlaggedDays>("/api/compliance/days", { query: { from, to } });
}

export function getEmMix(days: InsightDays): Promise<EmMix> {
  return request<EmMix>("/api/insights/em-mix", { query: { days } });
}
