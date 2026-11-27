import Link from "next/link";
import { DemoRequestButton } from "../DemoRequestButton";
import { Magnetic } from "../motion/Magnetic";
import { cssVars } from "../motion/cssVars";
import { LANDING_TEXT } from "../strings";
import styles from "./hero.module.css";

function Headline({ title }: { title: string }) {
  const words = title.split(" ");
  return (
    <h1 className="m-0 max-w-240 font-display text-display font-bold tracking-display sm:text-display-lg lg:text-hero xl:text-mega">
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

export function Hero() {
  const words = LANDING_TEXT.hero;
  return (
    <section className={styles.hero}>
      <div aria-hidden="true" className={styles.aurora} data-live="" />
      <div className="relative flex flex-col items-center gap-6">
        <Headline title={words.title} />
        <p className={`m-0 max-w-160 text-title3 text-secondary sm:text-title ${styles.lead}`}>{words.lead}</p>
        <div className={`mt-2 flex flex-wrap items-center justify-center gap-5 ${styles.ctas}`}>
          <Magnetic>
            <DemoRequestButton />
          </Magnetic>
          <Link href="/sign-in" className={`text-headline tracking-snug text-label ${styles.signIn}`}>
            {words.signIn}
          </Link>
        </div>
      </div>
    </section>
  );
}
