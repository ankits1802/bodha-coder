import type { LegalBlock, LegalDocumentData } from "./types";

const PLACEHOLDER = /\[[^\]]+\]/g;

export interface TextPart {
  text: string;
  placeholder: boolean;
}

export function placeholdersIn(text: string): string[] {
  return text.match(PLACEHOLDER) ?? [];
}

export function splitPlaceholders(text: string): TextPart[] {
  const parts: TextPart[] = [];
  let next = 0;
  for (const match of text.matchAll(PLACEHOLDER)) {
    if (match.index > next) parts.push({ text: text.slice(next, match.index), placeholder: false });
    parts.push({ text: match[0], placeholder: true });
    next = match.index + match[0].length;
  }
  if (next < text.length) parts.push({ text: text.slice(next), placeholder: false });
  return parts;
}

function blockTexts(block: LegalBlock): string[] {
  switch (block.kind) {
    case "bullets":
      return [...block.items];
    case "clauses":
      return block.items.flatMap((item) => [item.term, item.text]);
    case "table":
      return [block.table.caption, ...block.table.columns, ...block.table.rows.flat()];
    case "links":
      return [];
    default:
      return [block.text];
  }
}

export function documentTexts(document: LegalDocumentData): string[] {
  return [document.title, document.summary, ...document.sections.flatMap((section) => [section.heading, ...section.blocks.flatMap(blockTexts)])];
}
