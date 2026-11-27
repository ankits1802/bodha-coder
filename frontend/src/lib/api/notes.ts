import { request, requestNothing } from "./client";
import type {
  ApprovedNotes,
  AskBody,
  AssignedNotes,
  Choice,
  ComplianceDecision,
  ComplianceOutcome,
  DocumentLink,
  NoteDetail,
  NoteLane,
  NotePayer,
  NoteState,
  OverrideChoice,
  PayerOption,
  QueuedNotes,
  ReopenedNotes,
  RequestCancelled,
  RequestCreated,
  ReturnReasonChoice,
  VoidedNotes,
} from "./types";

const notePath = (noteId: string, suffix = ""): string => `/api/notes/${encodeURIComponent(noteId)}${suffix}`;

export function getNote(noteId: string): Promise<NoteDetail> {
  return request<NoteDetail>(notePath(noteId));
}

export function getNoteDocument(noteId: string): Promise<DocumentLink> {
  return request<DocumentLink>(notePath(noteId, "/document"));
}

export function replaceNoteDocument(noteId: string, file: File): Promise<NoteState> {
  const form = new FormData();
  form.set("file", file, file.name);
  return request<NoteState>(notePath(noteId, "/document"), { method: "POST", form });
}

export function saveDecisions(
  noteId: string,
  choices: Record<string, Choice>,
  reasons: Record<string, OverrideChoice> = {},
): Promise<NoteDetail> {
  return request<NoteDetail>(notePath(noteId, "/decisions"), { method: "PUT", body: { choices, reasons } });
}

export function saveBilledCodes(noteId: string, codes: string, reason: OverrideChoice): Promise<NoteDetail> {
  return request<NoteDetail>(notePath(noteId, "/billed-codes"), { method: "PUT", body: { codes, reason } });
}

export function approveNote(noteId: string): Promise<NoteState> {
  return request<NoteState>(notePath(noteId, "/approve"), { method: "POST" });
}

export function approveNotes(noteIds: string[]): Promise<ApprovedNotes> {
  return request<ApprovedNotes>("/api/notes/approve", { body: { note_ids: noteIds } });
}

export function flagNote(noteId: string, reason: string): Promise<NoteLane> {
  return request<NoteLane>(notePath(noteId, "/flag"), { body: { reason } });
}

export function decideCompliance(
  noteId: string,
  decision: ComplianceDecision,
  reason: string | null,
): Promise<ComplianceOutcome> {
  return request<ComplianceOutcome>(notePath(noteId, "/compliance"), { body: { decision, reason } });
}

export function returnToCoder(noteId: string, returnReason: ReturnReasonChoice): Promise<ComplianceOutcome> {
  return request<ComplianceOutcome>(notePath(noteId, "/compliance"), {
    body: { decision: "return", reason: null, return_reason: returnReason },
  });
}

export function getPayers(): Promise<PayerOption[]> {
  return request<PayerOption[]>("/api/payers");
}

export function setNotePayer(noteId: string, payer: string | null): Promise<NotePayer> {
  return request<NotePayer>(notePath(noteId, "/payer"), { method: "PUT", body: { payer } });
}

export function voidNotes(noteIds: string[], reason: string): Promise<VoidedNotes> {
  return request<VoidedNotes>("/api/notes/void", { body: { note_ids: noteIds, reason } });
}

export function restoreNote(noteId: string, reason: string): Promise<NoteState> {
  return request<NoteState>(notePath(noteId, "/restore"), { body: { reason } });
}

export function assignNotes(noteIds: string[], userId: string | null): Promise<AssignedNotes> {
  return request<AssignedNotes>("/api/notes/assign", { body: { note_ids: noteIds, user_id: userId } });
}

export function changeVisitType(noteId: string, visitType: string): Promise<NoteState> {
  return request<NoteState>(notePath(noteId, "/visit-type"), { method: "PUT", body: { visit_type: visitType } });
}

export function cancelRequest(noteId: string): Promise<RequestCancelled> {
  return request<RequestCancelled>(notePath(noteId, "/cancel-request"), { method: "POST" });
}

export function reopenNote(noteId: string): Promise<NoteState> {
  return request<NoteState>(notePath(noteId, "/reopen"), { method: "POST" });
}

export function reopenNotes(noteIds: string[]): Promise<ReopenedNotes> {
  return request<ReopenedNotes>("/api/notes/reopen", { body: { note_ids: noteIds } });
}

export function retryFailedNotes(noteIds: string[] | null): Promise<QueuedNotes> {
  return request<QueuedNotes>("/api/notes/retry", { body: { note_ids: noteIds } });
}

export function retryNote(noteId: string): Promise<NoteState> {
  return request<NoteState>(notePath(noteId, "/retry"), { method: "POST" });
}

export function askProvider(noteId: string, body: AskBody): Promise<RequestCreated> {
  return request<RequestCreated>(notePath(noteId, "/ask"), { body });
}

export function remindProvider(noteId: string): Promise<void> {
  return requestNothing(notePath(noteId, "/remind"), { method: "POST" });
}
