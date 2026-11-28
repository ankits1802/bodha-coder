import type { PracticeSetup, SetupSectionKey } from "@/lib/api/types";
import { isNpiShaped } from "@/lib/validation";
import { SETUP_TEXT, type SetupNavKey } from "./strings";

type ScoredKey = SetupSectionKey | "providers";

export const SECTION_ORDER: readonly ScoredKey[] = [
  "practice_details",
  "providers",
  "payers",
  "payments",
  "coding_rules",
  "charge_capture",
  "documentation_rules",
  "compliance",
  "reports",
  "contacts",
  "patient_registration",
  "software",
];

const UNSCORED: readonly SetupNavKey[] = ["checks", "intake", "ehr", "mips"];

function isScored(key: SetupNavKey): key is ScoredKey {
  return (SECTION_ORDER as readonly string[]).includes(key);
}

export const NAV_ORDER: readonly SetupNavKey[] = [...SECTION_ORDER, ...UNSCORED];

export type SectionMarker = "complete" | "incomplete" | "attention" | "none";

export function isNavKey(value: string | null): value is SetupNavKey {
  return value !== null && (NAV_ORDER as readonly string[]).includes(value);
}

export function markerFor(key: SetupNavKey, setup: PracticeSetup): SectionMarker {
  if (!isScored(key)) return "none";
  if (key === "providers" && setup.missing_npi > 0) return "attention";
  return setup.sections[key]?.complete ? "complete" : "incomplete";
}

export function fieldLabel(field: string): string {
  const known = SETUP_TEXT.fields[field];
  if (known) return known;
  const words = field.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function valuesFor(fields: string[], stored: Record<string, string>): Record<string, string> {
  return Object.fromEntries(fields.map((field) => [field, stored[field] ?? ""]));
}

export function sameValues(left: Record<string, string>, right: Record<string, string>): boolean {
  const keys = new Set([...Object.keys(left), ...Object.keys(right)]);
  return [...keys].every((key) => (left[key] ?? "") === (right[key] ?? ""));
}

const EIN_PATTERN = /^\d{2}-?\d{7}$/;

const FIELD_CHECKS: Record<string, (value: string) => boolean> = {
  group_npi: isNpiShaped,
  tax_id: (value) => EIN_PATTERN.test(value.trim()),
};

export function fieldError(field: string, value: string): string | null {
  const check = FIELD_CHECKS[field];
  if (!check || value.trim() === "" || check(value)) return null;
  return SETUP_TEXT.fieldErrors[field] ?? null;
}

export function nextIncomplete(setup: PracticeSetup, after: SetupNavKey): SetupNavKey | null {
  if (!isScored(after) || markerFor(after, setup) !== "complete") return null;
  const start = SECTION_ORDER.indexOf(after);
  return SECTION_ORDER.slice(start + 1).find((key) => markerFor(key, setup) !== "complete") ?? null;
}