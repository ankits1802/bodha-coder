import Link from "next/link";
import { CheckMark } from "@/components/ui/CheckMark";
import { DemoRequestButton } from "../DemoRequestButton";
import { Magnetic } from "../motion/Magnetic";
import { cssVars } from "../motion/cssVars";
import { StartTrialButton } from "../StartTrialButton";
import { LANDING_TEXT } from "../strings";
import styles from "./hero.module.css";
import { HeroSlice } from "./HeroSlice";

function Headline({ title }: { title: string }) {
  const words = title.split(" ");
  return (
    <h1 className="m-0 max-w-240 font-display text-hero-sm font-bold tracking-display sm:text-display-lg xl:text-hero">
      <span className="sr-only">{title}</span>
      <span aria-hidden="true">
        {words.map((word, index) => (
          <span key={`${word}-${index}`}>
            <span
              className={index === words.length - 1 ? `${styles.word} ${styles.defend}` : styles.word}
              style={cssVars({ "--i": index })}
            >
              {word}
            </span>
            {index < words.length - 1 ? " " : null}
          </span>
        ))}
      </span>
    </h1>
  );
}

function Backdrop() {
  return (
    <div aria-hidden="true" className={styles.backdrop} data-live="">
      <div className={styles.aurora} />
      <div className={styles.grid} />
    </div>
  );
}

function Facts({ facts }: { facts: readonly string[] }) {
  return (
    <ul className={styles.facts}>
      {facts.map((fact, index) => (
        <li key={fact} className={styles.fact} style={cssVars({ "--i": index })}>
          <span className={styles.factMark}>
            <CheckMark />
          </span>
          {fact}
        </li>
      ))}
    </ul>
  );
}

export function Hero() {
  const words = LANDING_TEXT.hero;
  return (
    <section className={styles.hero}>
      <Backdrop />
      <div className={styles.layout}>
        <div className={styles.copy}>
          <Headline title={words.title} />
          <p className={`m-0 max-w-160 text-headline text-secondary sm:text-title3 ${styles.lead}`}>{words.lead}</p>
          <div className={styles.ctas}>
            <Magnetic>
              <span className={styles.press}>
                <StartTrialButton label={LANDING_TEXT.startTrial} />
              </span>
            </Magnetic>
            <span className={styles.press}>
              <DemoRequestButton />
            </span>
            <Link href="/sign-in" className={`text-headline tracking-snug text-label ${styles.signIn}`}>
              {words.signIn}
            </Link>
          </div>
          <Facts facts={words.facts} />
        </div>
        <HeroSlice />
      </div>
    </section>
  );
}
