import { SECTION_IDS } from "./anchors";
import { DemoRequestButton } from "./DemoRequestButton";
import { Magnetic } from "./motion/Magnetic";
import { cssVars } from "./motion/cssVars";
import { StartTrialButton } from "./StartTrialButton";
import styles from "./sections/sections.module.css";
import { LANDING_TEXT } from "./strings";

export function ClosingCta() {
  const { demo } = LANDING_TEXT;
  const words = demo.title.split(" ");
  return (
    <section id={SECTION_IDS.demo} className={styles.closing}>
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
      <div data-reveal="" className="relative flex flex-wrap items-center justify-center gap-5" style={cssVars({ "--delay": "420ms" })}>
        <Magnetic>
          <StartTrialButton label={LANDING_TEXT.startTrial} />
        </Magnetic>
        <DemoRequestButton />
      </div>
    </section>
  );
}
