const PROCEDURE_CODE = /^\d{4}[0-9A-Z]/;

export interface CodeHint {
  before: string | null;
  after: string;
}

export function codeHint(billed: string[], suggested: string[]): CodeHint | null {
  const after = suggested[0];
  if (!after) return null;
  if (!PROCEDURE_CODE.test(after)) return { before: null, after };
  const before = billed.find((code) => PROCEDURE_CODE.test(code)) ?? null;
  return { before, after };
}
