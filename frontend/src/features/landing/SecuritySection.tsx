import { SECTION_IDS } from "./anchors";
import { cssVars } from "./motion/cssVars";
import { Safeguards } from "./sections/Safeguards";
import styles from "./sections/sections.module.css";
import { LANDING_TEXT } from "./strings";

function Vault() {
  return (
    <div aria-hidden="true" className={styles.vault} data-live="">
      <span className={`${styles.ring} ${styles.ringOuter}`} />
      <span className={`${styles.ring} ${styles.ringMiddle}`} />
      <span className={`${styles.ring} ${styles.ringInner}`} />
      <span className={styles.core}>
        <svg viewBox="0 0 24 24" width="30" height="30">
          <rect x="5" y="10.5" width="14" height="10" rx="2.5" className="fill-label" />
          <path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" fill="none" className="stroke-label" strokeWidth="2" />
        </svg>
      </span>
    </div>
  );
}

export function SecuritySection() {
  const words = LANDING_TEXT.security;
  return (
    <section id={SECTION_IDS.security} aria-labelledby="security-title" className="scroll-mt-16 overflow-hidden px-6 py-28 sm:py-30">
      <div className="mx-auto max-w-landing">
        <div className="grid items-center gap-10 md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] md:gap-14">
          <div data-reveal="" className="flex justify-center">
            <Vault />
          </div>
          <div className="min-w-0">
            <h2 id="security-title" data-reveal="" className="m-0 font-display text-hero-sm font-bold tracking-display sm:text-display">
              {words.title}
            </h2>
            <p data-reveal="" style={cssVars({ "--delay": "80ms" })} className="mt-4 mb-0 max-w-115 text-title3 text-secondary">
              {words.lead}
            </p>
          </div>
        </div>
        <Safeguards />
      </div>
    </section>
  );
}
