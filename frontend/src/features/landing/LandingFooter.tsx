import Link from "next/link";
import type { ReactNode } from "react";
import { SHARED_TEXT } from "@/components/shared/strings";
import { SIGN_UP_PATH } from "@/lib/api/auth";
import { FOOTER_SECTIONS, sectionHref } from "./anchors";
import { DemoRequestButton } from "./DemoRequestButton";
import { LANDING_TEXT } from "./strings";

const LINK = "text-label-soft hover:text-label";

function FooterNav({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <nav aria-labelledby={id}>
      <h2 id={id} className="m-0 text-footnote font-semibold text-label">
        {title}
      </h2>
      <ul className="mt-3.5 mb-0 flex list-none flex-col gap-2.5 p-0 text-label-soft">{children}</ul>
    </nav>
  );
}

export function LandingFooter() {
  const { footer, sections } = LANDING_TEXT;
  return (
    <footer className="border-t border-separator bg-muted-panel">
      <div className="mx-auto grid max-w-landing grid-cols-2 gap-x-6 gap-y-10 px-6 pt-14 pb-10 text-callout sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)]">
        <div className="col-span-2 sm:col-span-1">
          <Link href="/" className="text-input font-semibold tracking-snug text-label">
            {SHARED_TEXT.brand}
          </Link>
          <p className="mt-2 mb-0 max-w-70 text-secondary">{footer.tagline}</p>
        </div>
        <FooterNav id="footer-product" title={footer.product}>
          {FOOTER_SECTIONS.map((key) => (
            <li key={key}>
              <a href={sectionHref(key)} className={LINK}>
                {sections[key]}
              </a>
            </li>
          ))}
        </FooterNav>
        <FooterNav id="footer-start" title={footer.start}>
          <li>
            <Link href={SIGN_UP_PATH} className={LINK}>
              {LANDING_TEXT.startTrial}
            </Link>
          </li>
          <li>
            <DemoRequestButton variant="link" />
          </li>
          <li>
            <Link href="/sign-in" className={LINK}>
              {footer.signIn}
            </Link>
          </li>
        </FooterNav>
      </div>
      <div className="mx-auto max-w-landing px-6">
        <p className="m-0 border-t border-separator py-5 text-footnote text-secondary">{footer.copyright}</p>
      </div>
    </footer>
  );
}
