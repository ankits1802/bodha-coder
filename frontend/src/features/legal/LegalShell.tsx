import Link from "next/link";
import type { ReactNode } from "react";
import { LEGAL_INDEX_PATH, LEGAL_SLUGS, legalPath } from "@/components/shared/legal/legalLinks";
import { SHARED_TEXT } from "@/components/shared/strings";
import { LEGAL_TITLES } from "./content/headings";
import { LEGAL_TEXT } from "./strings";

const MAIN_ID = "legal-main";
const FOOTER_ID = "legal-footer";

export function LegalShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-surface text-label">
      <a
        href={`#${MAIN_ID}`}
        className="sr-only rounded-control bg-surface px-3 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50"
      >
        {SHARED_TEXT.skipToContent}
      </a>
      <header className="border-b border-separator print:hidden">
        <div className="mx-auto flex min-h-13 max-w-landing items-center justify-between gap-4 px-6 py-2">
          <Link href="/" className="text-input font-semibold tracking-snug text-label">
            {SHARED_TEXT.brand}
          </Link>
          <Link href={LEGAL_INDEX_PATH} className="text-callout text-label-soft hover:text-label">
            {LEGAL_TEXT.legal}
          </Link>
        </div>
      </header>
      <main id={MAIN_ID} tabIndex={-1} className="mx-auto w-full max-w-landing flex-1 px-6 pt-10 pb-20 outline-none sm:pt-14">
        {children}
      </main>
      <footer className="border-t border-separator bg-muted-panel print:hidden">
        <nav aria-labelledby={FOOTER_ID} className="mx-auto max-w-landing px-6 py-10">
          <h2 id={FOOTER_ID} className="m-0 text-footnote font-semibold text-label">
            {LEGAL_TEXT.documents}
          </h2>
          <ul className="mt-3.5 mb-0 flex list-none flex-wrap gap-x-6 gap-y-2.5 p-0 text-callout">
            {LEGAL_SLUGS.map((slug) => (
              <li key={slug}>
                <Link href={legalPath(slug)} className="text-label-soft hover:text-label">
                  {LEGAL_TITLES[slug]}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </footer>
    </div>
  );
}
