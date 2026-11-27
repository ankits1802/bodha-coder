import type { CheckKey, Checks } from "@/lib/api/types";

export const CHECK_ORDER: readonly CheckKey[] = ["em", "icd", "cdi", "audit", "mips", "hcc"];

export function withAllChecks(checks: Checks): Checks {
  return { ...checks, hcc: checks.hcc ?? false };
}

export function sameChecks(left: Checks, right: Checks): boolean {
  return CHECK_ORDER.every((key) => (left[key] ?? false) === (right[key] ?? false));
}
