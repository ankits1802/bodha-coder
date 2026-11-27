import type { Choice, Finding, OverrideChoice, OverrideReason } from "@/lib/api/types";

export const OVERRIDE_REASONS: readonly OverrideReason[] = [
  "documentation",
  "payer_policy",
  "provider_answer",
  "coding_guideline",
  "clinical_context",
  "other",
];

export const OVERRIDE_NOTE_MAX = 500;

export interface OverrideDraft {
  reason: OverrideReason | null;
  note: string;
}

export type OverrideProblem = "choose" | "note" | "long";

export const EMPTY_OVERRIDE: OverrideDraft = { reason: null, note: "" };

export function reasonForKey(key: string): OverrideReason | null {
  const position = Number.parseInt(key, 10);
  if (!/^[1-9]$/.test(key) || position > OVERRIDE_REASONS.length) return null;
  return OVERRIDE_REASONS[position - 1] ?? null;
}

export function overrideProblem(draft: OverrideDraft): OverrideProblem | null {
  if (draft.reason === null) return "choose";
  const note = draft.note.trim();
  if (note.length > OVERRIDE_NOTE_MAX) return "long";
  if (draft.reason === "other" && note === "") return "note";
  return null;
}

export function toOverride(draft: OverrideDraft): OverrideChoice | null {
  if (draft.reason === null || overrideProblem(draft) !== null) return null;
  const note = draft.note.trim();
  return { reason: draft.reason, note: note === "" ? null : note };
}

export function departsWith(finding: Finding, choice: Choice): boolean {
  return finding.departing_choices.includes(choice);
}
