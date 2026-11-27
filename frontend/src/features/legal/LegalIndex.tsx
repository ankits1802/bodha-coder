import Link from "next/link";
import { LEGAL_SLUGS, legalPath } from "@/components/shared/legal/legalLinks";
import { formatCalendarDay } from "@/lib/format";
import { DraftLabel } from "./DraftLabel";
import { LEGAL_DOCUMENTS } from "./documents";
import { LEGAL_TEXT } from "./strings";

export function LegalIndex({ draft }: { draft: boolean }) {
  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-4">
        {draft ? <DraftLabel /> : null}
        <h1 className="m-0 text-large-title font-bold tracking-title">{LEGAL_TEXT.legal}</h1>
      </header>
      <ul className="m-0 grid list-none gap-4 p-0 sm:grid-cols-2 lg:grid-cols-3">
        {LEGAL_SLUGS.map((slug) => {
          const document = LEGAL_DOCUMENTS[slug];
          return (
            <li key={slug}>
              <Link
                href={legalPath(slug)}
                className="flex h-full flex-col gap-2 rounded-panel bg-surface p-5 shadow-panel transition-shadow hover:shadow-float"
              >
                <span className="text-headline font-semibold tracking-headline text-label">{document.title}</span>
                <span className="text-body text-secondary">{document.summary}</span>
                <span className="mt-auto pt-2 text-footnote text-secondary">
                  {LEGAL_TEXT.version} {document.version} · {LEGAL_TEXT.updated} {formatCalendarDay(document.updated, "year")}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
