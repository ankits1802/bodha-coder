import type { BlindAnswer } from "@/lib/api/types";
import { BLIND_TEXT } from "./strings";

export interface AnswerDraft {
  em: string;
  icd: string;
  modifiers: string;
}

export type AnswerField = keyof AnswerDraft;
export type AnswerErrors = Partial<Record<AnswerField, string>>;

export type ParsedAnswer = { ok: true; answer: BlindAnswer } | { ok: false; errors: AnswerErrors };

export const EMPTY_DRAFT: AnswerDraft = { em: "", icd: "", modifiers: "" };

const EM_PATTERN = /^99\d{3}$/;
const ICD_PATTERN = /^[A-Z]\d[0-9A-Z](\.?[0-9A-Z]{1,4})?$/;
const MODIFIER_PATTERN = /^[0-9A-Z]{2}$/;
const SEPARATORS = /[\s,;]+/;

export function splitCodes(text: string): string[] {
  const codes = text
    .split(SEPARATORS)
    .map((code) => code.trim().toUpperCase())
    .filter(Boolean);
  return [...new Set(codes)];
}

function invalid(codes: string[], pattern: RegExp): string[] {
  return codes.filter((code) => !pattern.test(code));
}

export function parseAnswer(draft: AnswerDraft): ParsedAnswer {
  const em = draft.em.trim().toUpperCase();
  const icd = splitCodes(draft.icd);
  const modifiers = splitCodes(draft.modifiers);
  const errors: AnswerErrors = {};
  if (!em && icd.length === 0) errors.em = BLIND_TEXT.errors.empty;
  if (em && !EM_PATTERN.test(em)) errors.em = BLIND_TEXT.errors.em;
  const badIcd = invalid(icd, ICD_PATTERN);
  if (badIcd.length > 0) errors.icd = BLIND_TEXT.errors.icd(badIcd.join(", "));
  const badModifiers = invalid(modifiers, MODIFIER_PATTERN);
  if (badModifiers.length > 0) errors.modifiers = BLIND_TEXT.errors.modifiers(badModifiers.join(", "));
  if (Object.keys(errors).length > 0) return { ok: false, errors };
  return { ok: true, answer: { em: em || null, icd, modifiers } };
}
