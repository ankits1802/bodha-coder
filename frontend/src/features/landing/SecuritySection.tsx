import { cssVars } from "./motion/cssVars";
import styles from "./sections/sections.module.css";
import { LANDING_TEXT } from "./strings";

function CheckCircle() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true" className={`flex-none text-ok ${styles.check}`}>
      <circle cx="11" cy="11" r="11" fill="currentColor" />
      <path d="M6.5 11.3l3 3 6-6.3" pathLength={1} fill="none" stroke="var(--color-white, #fff)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Vault() {
  return (
    <div aria-hidden="true" className={styles.vault} data-live="">
      <span className={`${styles.ring} ${styles.ringOuter}`} />
      <span className={`${styles.ring} ${styles.ringMiddle}`} />
      <span className={`${styles.ring} ${styles.ringInner}`} />
      <span className={styles.core}>
        <svg viewBox="0 0 24 24" width="30" height="30">
          <rect x="5" y="10.5" width="14" height="10" rx="2.5" fill="#1D1D1F" />
          <path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" fill="none" stroke="#1D1D1F" strokeWidth="2" />
        </svg>
      </span>
    </div>
  );
}

export function SecuritySection() {
  const words = LANDING_TEXT.security;
  return (
    <section id="security" className="scroll-mt-16 overflow-hidden px-6 py-30">
      <div className="mx-auto grid max-w-landing items-center gap-14 md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <div data-reveal="" className="flex justify-center">
          <Vault />
        </div>
        <div className="min-w-0">
          <h2 data-reveal="" className="m-0 font-display text-hero-sm font-bold tracking-display sm:text-display">
            {words.title}
          </h2>
          <p data-reveal="" style={cssVars({ "--delay": "80ms" })} className="mt-4 mb-0 max-w-115 text-title3 text-secondary">
            {words.lead}
          </p>
          <ul className="mt-9 mb-0 flex list-none flex-col gap-4.5 p-0">
            {words.items.map((item, index) => (
              <li
                key={item}
                data-reveal=""
                style={cssVars({ "--delay": `${160 + index * 90}ms` })}
                className="flex items-center gap-3 text-headline tracking-snug"
              >
                <CheckCircle />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
