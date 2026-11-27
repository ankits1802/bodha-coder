import { request, requestNothing } from "./client";
import type { AskBody, Choice, ComplianceDecision, Lane, NoteDetail, NoteStatus } from "./types";

const notePath = (noteId: string, suffix = ""): string => `/api/notes/${encodeURIComponent(noteId)}${suffix}`;

export function getNote(noteId: string): Promise<NoteDetail> {
  return request<NoteDetail>(notePath(noteId));
}

export function getNoteDocument(noteId: string): Promise<{ url: string }> {
  return request<{ url: string }>(notePath(noteId, "/document"));
}

export function replaceNoteDocument(noteId: string, file: File): Promise<{ status: NoteStatus }> {
  const form = new FormData();
  form.set("file", file, file.name);
  return request<{ status: NoteStatus }>(notePath(noteId, "/document"), { method: "POST", form });
}

export function saveDecisions(noteId: string, choices: Record<string, Choice>): Promise<NoteDetail> {
  return request<NoteDetail>(notePath(noteId, "/decisions"), { method: "PUT", body: { choices } });
}

export function saveBilledCodes(noteId: string, codes: string): Promise<NoteDetail> {
  return request<NoteDetail>(notePath(noteId, "/billed-codes"), { method: "PUT", body: { codes } });
}

export function approveNote(noteId: string): Promise<{ status: NoteStatus }> {
  return request<{ status: NoteStatus }>(notePath(noteId, "/approve"), { method: "POST" });
}

export function approveNotes(noteIds: string[]): Promise<{ approved: string[] }> {
  return request<{ approved: string[] }>("/api/notes/approve", { body: { note_ids: noteIds } });
}

export function flagNote(noteId: string, reason: string): Promise<{ lane: Lane | null }> {
  return request<{ lane: Lane | null }>(notePath(noteId, "/flag"), { body: { reason } });
}

export function decideCompliance(
  noteId: string,
  decision: ComplianceDecision,
  reason: string | null,
): Promise<{ status: NoteStatus; lane: Lane | null }> {
  return request<{ status: NoteStatus; lane: Lane | null }>(notePath(noteId, "/compliance"), { body: { decision, reason } });
}

export function deleteNotes(noteIds: string[]): Promise<{ deleted: string[] }> {
  return request<{ deleted: string[] }>("/api/notes/delete", { body: { note_ids: noteIds } });
}

export function assignNotes(noteIds: string[], userId: string | null): Promise<{ assigned: string[] }> {
  return request<{ assigned: string[] }>("/api/notes/assign", { body: { note_ids: noteIds, user_id: userId } });
}

export function changeVisitType(noteId: string, visitType: string): Promise<{ status: NoteStatus }> {
  return request<{ status: NoteStatus }>(notePath(noteId, "/visit-type"), { method: "PUT", body: { visit_type: visitType } });
}

export function cancelRequest(noteId: string): Promise<{ lane: string }> {
  return request<{ lane: string }>(notePath(noteId, "/cancel-request"), { method: "POST" });
}

export function reopenNote(noteId: string): Promise<{ status: NoteStatus }> {
  return request<{ status: NoteStatus }>(notePath(noteId, "/reopen"), { method: "POST" });
}

export function retryFailedNotes(noteIds: string[] | null): Promise<{ queued: string[] }> {
  return request<{ queued: string[] }>("/api/notes/retry", { body: { note_ids: noteIds } });
}

export function retryNote(noteId: string): Promise<{ status: NoteStatus }> {
  return request<{ status: NoteStatus }>(notePath(noteId, "/retry"), { method: "POST" });
}

export function askProvider(noteId: string, body: AskBody): Promise<{ request_id: string }> {
  return request<{ request_id: string }>(notePath(noteId, "/ask"), { body });
}

export function remindProvider(noteId: string): Promise<void> {
  return requestNothing(notePath(noteId, "/remind"), { method: "POST" });
}
