import type { LegalSlug } from "@/components/shared/legal/legalLinks";

export interface LegalClause {
  term: string;
  text: string;
}

export interface LegalTable {
  caption: string;
  columns: readonly string[];
  rows: readonly (readonly string[])[];
}

export type LegalBlock =
  | { kind: "paragraph"; text: string }
  | { kind: "notice"; text: string }
  | { kind: "subheading"; text: string }
  | { kind: "bullets"; items: readonly string[] }
  | { kind: "clauses"; items: readonly LegalClause[] }
  | { kind: "table"; table: LegalTable }
  | { kind: "links"; slugs: readonly LegalSlug[] };

export interface LegalSection {
  id: string;
  heading: string;
  blocks: readonly LegalBlock[];
}

export interface LegalDocumentData {
  slug: LegalSlug;
  title: string;
  summary: string;
  version: string;
  updated: string;
  numbered: boolean;
  sections: readonly LegalSection[];
}
