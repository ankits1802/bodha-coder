import Link from "next/link";
import { DemoRequestButton } from "./DemoRequestButton";
import { LANDING_TEXT } from "./strings";

export function LandingFooter() {
  const { demo, footer } = LANDING_TEXT;
  return (
    <>
      <section id="demo" className="flex flex-col items-center gap-5.5 border-t border-separator px-6 py-28 text-center">
        <h2 className="m-0 font-display text-hero-sm font-bold tracking-display sm:text-display-lg">{demo.title}</h2>
        <DemoRequestButton />
      </section>
      <footer className="border-t border-separator bg-muted-panel">
        <div className="mx-auto flex max-w-landing flex-wrap justify-between gap-x-6 gap-y-3 px-6 py-5.5 text-footnote text-secondary">
          <span>{footer.copyright}</span>
          <nav aria-label={footer.label} className="flex gap-5.5">
            <a href="#security" className="hover:text-label">
              {footer.security}
            </a>
            <Link href="/sign-in" className="hover:text-label">
              {footer.signIn}
            </Link>
          </nav>
        </div>
      </footer>
    </>
  );
}
