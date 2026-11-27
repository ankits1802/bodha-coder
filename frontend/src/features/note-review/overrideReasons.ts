import {
  REASON_NOTE_MAX,
  emptyReason,
  reasonAtKey,
  reasonProblem,
  toReasonChoice,
  type ReasonDraft,
  type ReasonProblem,
} from "@/components/shared/reason-picker/reasonDraft";
import type { Choice, Finding, OverrideChoice, OverrideReason } from "@/lib/api/types";

export const OVERRIDE_REASONS: readonly OverrideReason[] = [
  "documentation",
  "payer_policy",
  "provider_answer",
  "coding_guideline",
  "clinical_context",
  "other",
];

export const OVERRIDE_NOTE_MAX = REASON_NOTE_MAX;

export type OverrideDraft = ReasonDraft<OverrideReason>;

export type OverrideProblem = ReasonProblem;

export const EMPTY_OVERRIDE: OverrideDraft = emptyReason<OverrideReason>();

export function reasonForKey(key: string): OverrideReason | null {
  return reasonAtKey(OVERRIDE_REASONS, key);
}

export function overrideProblem(draft: OverrideDraft): OverrideProblem | null {
  return reasonProblem(draft);
}

export function toOverride(draft: OverrideDraft): OverrideChoice | null {
  return toReasonChoice(draft);
}

export function departsWith(finding: Finding, choice: Choice): boolean {
  return finding.departing_choices.includes(choice);
}
