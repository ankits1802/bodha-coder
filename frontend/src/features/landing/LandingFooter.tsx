import Link from "next/link";
import { DemoRequestButton } from "./DemoRequestButton";
import { Magnetic } from "./motion/Magnetic";
import { cssVars } from "./motion/cssVars";
import styles from "./sections/sections.module.css";
import { LANDING_TEXT } from "./strings";

export function LandingFooter() {
  const { demo, footer } = LANDING_TEXT;
  const words = demo.title.split(" ");
  return (
    <>
      <section id="demo" className={styles.closing}>
        <h2 className="relative m-0 max-w-200 font-display text-hero-sm font-bold tracking-display sm:text-display-lg lg:text-hero">
          <span className="sr-only">{demo.title}</span>
          <span aria-hidden="true">
            {words.map((word, index) => (
              <span key={`${word}-${index}`}>
                <span data-reveal="" className="inline-block" style={cssVars({ "--delay": `${index * 90}ms` })}>
                  {word}
                </span>
                {index < words.length - 1 ? " " : null}
              </span>
            ))}
          </span>
        </h2>
        <div data-reveal="" className="relative" style={cssVars({ "--delay": "420ms" })}>
          <Magnetic>
            <DemoRequestButton />
          </Magnetic>
        </div>
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
