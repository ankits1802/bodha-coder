import type { EhrConnection, EhrNoteType, EhrSettingsInput } from "@/lib/api/types";
import { EHR_TEXT } from "./strings";

export const NOTE_TYPES: readonly EhrNoteType[] = ["progress", "consult", "history_physical", "nursing_facility"];

export interface EhrDraft {
  baseUrl: string;
  clientId: string;
  scopes: string;
  noteTypes: readonly EhrNoteType[];
  startDate: string | null;
}

export interface EhrProblems {
  baseUrl: string | null;
  clientId: string | null;
  scopes: string | null;
  noteTypes: string | null;
  startDate: string | null;
}

const HTTPS = /^https:\/\/[^\s/?#]+/i;

export function draftFrom(view: EhrConnection): EhrDraft {
  const saved = view.connection;
  return {
    baseUrl: saved?.base_url ?? "",
    clientId: saved?.client_id ?? "",
    scopes: (saved?.scopes ?? view.default_scopes).join("\n"),
    noteTypes: saved?.note_types ?? ["progress"],
    startDate: saved?.start_date ?? null,
  };
}

export function scopesOf(text: string): string[] {
  return [...new Set(text.split(/\s+/).filter(Boolean))];
}

export function problemsOf(draft: EhrDraft): EhrProblems {
  return {
    baseUrl: HTTPS.test(draft.baseUrl.trim()) ? null : EHR_TEXT.errors.baseUrl,
    clientId: draft.clientId.trim() ? null : EHR_TEXT.errors.clientId,
    scopes: scopesOf(draft.scopes).length > 0 ? null : EHR_TEXT.errors.scopes,
    noteTypes: draft.noteTypes.length > 0 ? null : EHR_TEXT.errors.noteTypes,
    startDate: draft.startDate ? null : EHR_TEXT.errors.startDate,
  };
}

export function hasProblems(problems: EhrProblems): boolean {
  return Object.values(problems).some((problem) => problem !== null);
}

export function settingsFrom(draft: EhrDraft): EhrSettingsInput {
  return {
    base_url: draft.baseUrl.trim(),
    client_id: draft.clientId.trim(),
    scopes: scopesOf(draft.scopes),
    note_types: NOTE_TYPES.filter((type) => draft.noteTypes.includes(type)),
    start_date: draft.startDate ?? "",
  };
}

export function withNoteType(draft: EhrDraft, type: EhrNoteType, chosen: boolean): readonly EhrNoteType[] {
  const others = draft.noteTypes.filter((item) => item !== type);
  return chosen ? NOTE_TYPES.filter((item) => item === type || others.includes(item)) : others;
}
