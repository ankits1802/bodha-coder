import { request, requestNothing } from "./client";
import type { AskBody, Choice, ComplianceDecision, Lane, NoteDetail, NoteStatus } from "./types";

const notePath = (noteId: string, suffix = ""): string => `/api/notes/${encodeURIComponent(noteId)}${suffix}`;

export function getNote(noteId: string): Promise<NoteDetail> {
  return request<NoteDetail>(notePath(noteId));
}

export function getNoteDocument(noteId: string): Promise<{ url: string }> {
  return request<{ url: string }>(notePath(noteId, "/document"));
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

export function retryNote(noteId: string): Promise<{ status: NoteStatus }> {
  return request<{ status: NoteStatus }>(notePath(noteId, "/retry"), { method: "POST" });
}

export function askProvider(noteId: string, body: AskBody): Promise<{ request_id: string }> {
  return request<{ request_id: string }>(notePath(noteId, "/ask"), { body });
}

export function remindProvider(noteId: string): Promise<void> {
  return requestNothing(notePath(noteId, "/remind"), { method: "POST" });
}
