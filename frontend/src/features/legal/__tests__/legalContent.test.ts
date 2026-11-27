import { describe, expect, it } from "vitest";
import { LEGAL_SLUGS, type LegalSlug } from "@/components/shared/legal/legalLinks";
import { LEGAL_DRAFT, LEGAL_PARTY } from "../config";
import {
  AUP_HEADINGS,
  BAA_HEADINGS,
  PRIVACY_HEADINGS,
  SECURITY_HEADINGS,
  SUBPROCESSOR_HEADINGS,
  TERMS_HEADINGS,
} from "../content/headings";
import { LEGAL_DOCUMENTS } from "../documents";
import { documentTexts, placeholdersIn, splitPlaceholders } from "../placeholders";

const HEADINGS: Record<LegalSlug, Record<string, string>> = {
  terms: TERMS_HEADINGS,
  privacy: PRIVACY_HEADINGS,
  baa: BAA_HEADINGS,
  "acceptable-use": AUP_HEADINGS,
  subprocessors: SUBPROCESSOR_HEADINGS,
  security: SECURITY_HEADINGS,
};

const CONFIG_PLACEHOLDERS = new Set(Object.values(LEGAL_PARTY).flatMap(placeholdersIn));

function allPlaceholders(): string[] {
  return LEGAL_SLUGS.flatMap((slug) => documentTexts(LEGAL_DOCUMENTS[slug]).flatMap(placeholdersIn));
}

describe("legal content", () => {
  it.each(LEGAL_SLUGS)("uses every %s heading once, in the order the headings are listed", (slug) => {
    const document = LEGAL_DOCUMENTS[slug];
    expect(document.slug).toBe(slug);
    expect(document.sections.map((section) => section.id)).toEqual(Object.keys(HEADINGS[slug]));
    expect(document.sections.map((section) => section.heading)).toEqual(Object.values(HEADINGS[slug]));
  });

  it.each(LEGAL_SLUGS)("gives %s a version and an ISO last-updated date", (slug) => {
    const document = LEGAL_DOCUMENTS[slug];
    expect(document.version).toMatch(/^\d+\.\d+$/);
    expect(document.updated).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("takes every placeholder from the one legal configuration", () => {
    const stray = allPlaceholders().filter((placeholder) => !CONFIG_PLACEHOLDERS.has(placeholder));
    expect(stray).toEqual([]);
  });

  it("refuses to publish while any placeholder is left unfilled", () => {
    expect(LEGAL_DRAFT || allPlaceholders().length === 0).toBe(true);
  });

  it("keeps the product name and the company name in the configuration", () => {
    expect(LEGAL_PARTY.product).toBe("Bodha Coder");
    const terms = documentTexts(LEGAL_DOCUMENTS.terms).join(" ");
    expect(terms).toContain(`between ${LEGAL_PARTY.company}, ${LEGAL_PARTY.entity}`);
  });

  it("marks bracketed text as placeholders and leaves the rest as written", () => {
    expect(splitPlaceholders("Write to [email] or [address].")).toEqual([
      { text: "Write to ", placeholder: false },
      { text: "[email]", placeholder: true },
      { text: " or ", placeholder: false },
      { text: "[address]", placeholder: true },
      { text: ".", placeholder: false },
    ]);
    expect(splitPlaceholders("No placeholders here.")).toEqual([{ text: "No placeholders here.", placeholder: false }]);
  });

  it("never claims a certification the service does not hold", () => {
    const everything = LEGAL_SLUGS.flatMap((slug) => documentTexts(LEGAL_DOCUMENTS[slug])).join(" ");
    expect(everything).not.toMatch(/SOC 2|HITRUST|HIPAA certified|HIPAA-certified|ISO 27001/);
  });
});
