import { LEGAL_SLUGS, type LegalSlug } from "@/components/shared/legal/legalLinks";
import { ACCEPTABLE_USE } from "./content/acceptableUse";
import { BAA } from "./content/baa";
import { PRIVACY } from "./content/privacy";
import { SECURITY } from "./content/security";
import { SUBPROCESSORS } from "./content/subprocessors";
import { TERMS } from "./content/terms";
import type { LegalDocumentData } from "./types";

export const LEGAL_DOCUMENTS: Record<LegalSlug, LegalDocumentData> = {
  terms: TERMS,
  privacy: PRIVACY,
  baa: BAA,
  "acceptable-use": ACCEPTABLE_USE,
  subprocessors: SUBPROCESSORS,
  security: SECURITY,
};

export function isLegalSlug(value: string): value is LegalSlug {
  return (LEGAL_SLUGS as readonly string[]).includes(value);
}

export function legalDocument(slug: string): LegalDocumentData | null {
  return isLegalSlug(slug) ? LEGAL_DOCUMENTS[slug] : null;
}
