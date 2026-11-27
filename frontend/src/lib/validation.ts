const CPT_PATTERN = /^(\d{4}[0-9A-Z]|[A-Z]\d{4})$/;
const MODIFIER_PATTERN = /^[0-9A-Z]{2}$/;
const ICD_UNDOTTED = /^[A-TV-Z][0-9][0-9A-Z][0-9A-Z]{0,4}$/;
const MAX_MODIFIERS = 4;
const UNITS_SUFFIX = /^(.+?)\s*[X×]\s*(\d+)$/;
const CODE_PARTS = /[-\s]+/;
const MIN_UNITS = 1;
const MAX_UNITS = 99;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SIX_DIGITS = /^\d{6}$/;
const NPI_PATTERN = /^\d{10}$/;

export const PASSWORD_MIN_LENGTH = 10;
export const COMPLIANCE_REASON_MAX = 300;
export const VOID_REASON_MIN = 3;
export const VOID_REASON_MAX = 2000;

export interface ParsedCodes {
  codes: string[];
  invalid: string[];
}

function isIcdShaped(token: string): boolean {
  return ICD_UNDOTTED.test(token.replaceAll(".", ""));
}

function isProcedure(text: string): boolean {
  const [base = "", ...modifiers] = text.split(CODE_PARTS);
  return CPT_PATTERN.test(base) && modifiers.length <= MAX_MODIFIERS && modifiers.every((m) => MODIFIER_PATTERN.test(m));
}

function isValidCodeToken(token: string): boolean {
  const counted = UNITS_SUFFIX.exec(token);
  if (counted && isProcedure(counted[1] ?? "")) {
    const units = Number(counted[2]);
    return units >= MIN_UNITS && units <= MAX_UNITS;
  }
  if (isProcedure(token)) return true;
  if (CODE_PARTS.test(token)) return false;
  return (token.includes(".") || token.length === 3) && isIcdShaped(token);
}

export function parseCodeList(text: string): ParsedCodes {
  const codes: string[] = [];
  const invalid: string[] = [];
  for (const raw of text.split(/[,;\n]+/)) {
    const token = raw.trim().toUpperCase();
    if (!token) continue;
    if (isValidCodeToken(token)) codes.push(token);
    else invalid.push(raw.trim());
  }
  return { codes, invalid };
}

export function isEmail(text: string): boolean {
  return EMAIL_PATTERN.test(text.trim());
}

export function isSixDigitCode(text: string): boolean {
  return SIX_DIGITS.test(text);
}

export function isNpiShaped(text: string): boolean {
  return NPI_PATTERN.test(text.trim());
}
