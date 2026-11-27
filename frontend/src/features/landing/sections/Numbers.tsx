import { cssVars } from "../motion/cssVars";
import { LANDING_TEXT } from "../strings";
import { ApproveToy } from "./ApproveToy";
import { CountUp } from "./CountUp";
import styles from "./sections.module.css";

const DISPLAY = "font-display text-display-lg font-bold tracking-tightest tabular-nums";
const LABEL = "mt-1.5 mb-0 text-headline text-secondary";

export function Numbers() {
  const words = LANDING_TEXT.numbers;
  const [checked, both, click] = words.items;
  return (
    <section aria-label={words.label} className="bg-muted-panel px-6 py-28">
      <div className="mx-auto grid max-w-landing grid-cols-[repeat(auto-fit,minmax(15rem,1fr))] gap-12 text-center">
        <div data-reveal="" style={cssVars({ "--delay": "0ms" })}>
          <div className={DISPLAY}>
            <CountUp value={checked.value} />
          </div>
          <p className={LABEL}>{checked.label}</p>
        </div>
        <div data-reveal="" style={cssVars({ "--delay": "120ms" })}>
          <div className={`${DISPLAY} inline-flex items-center gap-3`}>
            <span aria-hidden="true" className={`${styles.arrow} ${styles.arrowUp}`}>
              ↑
            </span>
            {both.value}
            <span aria-hidden="true" className={`${styles.arrow} ${styles.arrowDown}`}>
              ↓
            </span>
          </div>
          <p className={LABEL}>{both.label}</p>
        </div>
        <div data-reveal="" style={cssVars({ "--delay": "240ms" })}>
          <div className={DISPLAY}>{click.value}</div>
          <p className={LABEL}>{click.label}</p>
          <div className="mt-5">
            <ApproveToy approve={words.approve} approved={words.approved} />
          </div>
        </div>
      </div>
    </section>
  );
}
