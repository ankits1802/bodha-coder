import { LEGAL_TEXT } from "./strings";
import type { LegalDocumentData } from "./types";

export const CONTENTS_ID = "legal-contents";

export function sectionNumber(document: LegalDocumentData, index: number): string | null {
  return document.numbered ? `${index + 1}.` : null;
}

export function LegalContents({ document }: { document: LegalDocumentData }) {
  return (
    <nav aria-labelledby={CONTENTS_ID} className="print:hidden lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)] lg:self-start lg:overflow-y-auto">
      <h2 id={CONTENTS_ID} className="m-0 text-subhead font-semibold text-secondary">
        {LEGAL_TEXT.contents}
      </h2>
      <ol className="mt-3 mb-0 flex list-none flex-col gap-2 p-0 text-callout">
        {document.sections.map((section, index) => (
          <li key={section.id}>
            <a href={`#${section.id}`} className="flex gap-1.5 text-label-soft hover:text-label hover:underline">
              {document.numbered ? <span className="w-6 flex-none tabular-nums text-secondary">{sectionNumber(document, index)} </span> : null}
              <span>{section.heading}</span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
