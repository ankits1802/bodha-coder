import type { LegalSlug } from "@/components/shared/legal/legalLinks";
import type { LegalBlock, LegalClause, LegalSection, LegalTable } from "./types";

export function paragraph(text: string): LegalBlock {
  return { kind: "paragraph", text };
}

export function notice(text: string): LegalBlock {
  return { kind: "notice", text };
}

export function subheading(text: string): LegalBlock {
  return { kind: "subheading", text };
}

export function bullets(...items: string[]): LegalBlock {
  return { kind: "bullets", items };
}

export function clauses(...pairs: (readonly [string, string])[]): LegalBlock {
  const items: LegalClause[] = pairs.map(([term, text]) => ({ term, text }));
  return { kind: "clauses", items };
}

export function table(table: LegalTable): LegalBlock {
  return { kind: "table", table };
}

export function links(...slugs: LegalSlug[]): LegalBlock {
  return { kind: "links", slugs };
}

export function section<Id extends string>(id: Id, headings: Record<Id, string>, ...blocks: LegalBlock[]): LegalSection {
  return { id, heading: headings[id], blocks };
}
