import type { PracticeMeasure, PracticeMeasureInput } from "@/lib/api/types";
import { PRACTICE_MEASURE_TEXT } from "./strings";

export const MEASURE_LIMITS = {
  nameMin: 3,
  nameMax: 80,
  identifierMax: 20,
  textMin: 10,
  scopeMax: 600,
  toMeetMax: 1000,
  codesPerOutcome: 4,
} as const;

export interface MeasureDraft {
  name: string;
  identifier: string;
  in_scope: string;
  out_of_scope: string;
  to_meet: string;
  met_codes: string;
  not_met_codes: string;
}

export type MeasureErrors = Partial<Record<keyof MeasureDraft, string>>;

const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9 ./_-]*$/;
const MEASURE_NUMBER = /^(?:mips\s*)?(?:quality\s*id\s*)?#?\s*\d{1,3}$|^p\d{3}$/i;
const REPORTING_CODE = /^(?:\d{4}[0-9A-Z]|[A-Z]\d{4})(?:-[0-9A-Z]{2})?$/;
const CODE_SEPARATORS = /[\s,;]+/;

export function draftFrom(measure: PracticeMeasure | null): MeasureDraft {
  return {
    name: measure?.name ?? "",
    identifier: measure?.identifier ?? "",
    in_scope: measure?.in_scope ?? "",
    out_of_scope: measure?.out_of_scope ?? "",
    to_meet: measure?.to_meet ?? "",
    met_codes: measure?.met_codes.join(", ") ?? "",
    not_met_codes: measure?.not_met_codes.join(", ") ?? "",
  };
}

export function codesFrom(text: string): string[] {
  const codes = text.toUpperCase().split(CODE_SEPARATORS).filter(Boolean);
  return codes.filter((code, index) => codes.indexOf(code) === index);
}

function lengthError(text: string, minimum: number, maximum: number, message: string): string | undefined {
  const length = text.trim().length;
  return length < minimum || length > maximum ? message : undefined;
}

function identifierError(identifier: string): string | undefined {
  const words = PRACTICE_MEASURE_TEXT.dialog.errors;
  const text = identifier.trim();
  if (!text) return undefined;
  if (MEASURE_NUMBER.test(text)) return words.identifierNumber;
  return text.length > MEASURE_LIMITS.identifierMax || !IDENTIFIER.test(text) ? words.identifier : undefined;
}

function codesError(codes: string[]): string | undefined {
  const fits = codes.length <= MEASURE_LIMITS.codesPerOutcome && codes.every((code) => REPORTING_CODE.test(code));
  return fits ? undefined : PRACTICE_MEASURE_TEXT.dialog.errors.codes;
}

export function validateDraft(draft: MeasureDraft): MeasureErrors {
  const words = PRACTICE_MEASURE_TEXT.dialog.errors;
  const met = codesFrom(draft.met_codes);
  const notMet = codesFrom(draft.not_met_codes);
  const errors: MeasureErrors = {
    name: lengthError(draft.name, MEASURE_LIMITS.nameMin, MEASURE_LIMITS.nameMax, words.name),
    identifier: identifierError(draft.identifier),
    in_scope: lengthError(draft.in_scope, MEASURE_LIMITS.textMin, MEASURE_LIMITS.scopeMax, words.inScope),
    out_of_scope: lengthError(draft.out_of_scope, 0, MEASURE_LIMITS.scopeMax, words.outOfScope),
    to_meet: lengthError(draft.to_meet, MEASURE_LIMITS.textMin, MEASURE_LIMITS.toMeetMax, words.toMeet),
    met_codes: codesError(met),
    not_met_codes: codesError(notMet) ?? (notMet.some((code) => met.includes(code)) ? words.bothOutcomes : undefined),
  };
  return Object.fromEntries(Object.entries(errors).filter(([, message]) => message !== undefined));
}

export function inputFrom(draft: MeasureDraft): PracticeMeasureInput {
  return {
    name: draft.name.trim(),
    identifier: draft.identifier.trim() || null,
    in_scope: draft.in_scope.trim(),
    out_of_scope: draft.out_of_scope.trim() || null,
    to_meet: draft.to_meet.trim(),
    met_codes: codesFrom(draft.met_codes),
    not_met_codes: codesFrom(draft.not_met_codes),
  };
}
