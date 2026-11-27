import { formatCalendarDay } from "@/lib/format";
import { LEGAL_PARTY } from "./config";
import { DraftLabel } from "./DraftLabel";
import { LegalContents, sectionNumber } from "./LegalContents";
import { LegalSectionView } from "./LegalSectionView";
import { LegalText } from "./LegalText";
import { LEGAL_TEXT } from "./strings";
import type { LegalDocumentData } from "./types";

const TITLE_ID = "legal-title";

function Fact({ term, value }: { term: string; value: string }) {
  return (
    <div className="flex gap-1.5">
      <dt>{term}</dt>
      <dd className="m-0 text-label-soft">
        <LegalText text={value} />
      </dd>
    </div>
  );
}

function LegalHeader({ document, draft }: { document: LegalDocumentData; draft: boolean }) {
  return (
    <header className="flex max-w-prose flex-col gap-4">
      {draft ? <DraftLabel /> : null}
      <h1 id={TITLE_ID} className="m-0 text-large-title font-bold tracking-title">
        {document.title}
      </h1>
      <dl className="m-0 flex flex-wrap gap-x-6 gap-y-1.5 text-subhead text-secondary">
        <Fact term={LEGAL_TEXT.version} value={document.version} />
        <Fact term={LEGAL_TEXT.updated} value={formatCalendarDay(document.updated, "year")} />
        <Fact term={LEGAL_TEXT.effective} value={LEGAL_PARTY.effectiveDate} />
      </dl>
    </header>
  );
}

export function LegalDocument({ document, draft }: { document: LegalDocumentData; draft: boolean }) {
  return (
    <article aria-labelledby={TITLE_ID}>
      <LegalHeader document={document} draft={draft} />
      <div className="mt-10 grid grid-cols-1 gap-10 border-t border-separator pt-10 lg:grid-cols-[minmax(0,14rem)_minmax(0,1fr)] lg:gap-16 print:block print:border-0 print:pt-0">
        <LegalContents document={document} />
        <div className="flex min-w-0 max-w-prose flex-col gap-12 text-input leading-relaxed text-label print:max-w-none">
          {document.sections.map((section, index) => (
            <LegalSectionView key={section.id} section={section} number={sectionNumber(document, index)} />
          ))}
        </div>
      </div>
    </article>
  );
}
