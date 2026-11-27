import { Fragment } from "react";
import { CheckMark } from "@/components/ui/CheckMark";
import { CodeChange } from "@/components/ui/CodeChange";
import { CodeChip } from "@/components/ui/CodeChip";
import { highlightSegments } from "@/lib/highlight";
import { cssVars } from "../motion/cssVars";
import { LANDING_TEXT } from "../strings";
import styles from "./slice.module.css";

type Suggestion = (typeof LANDING_TEXT.product.suggestions)[number];

const words = LANDING_TEXT.product;
const ACCEPT_KEY = LANDING_TEXT.deskUi.queue.keys[0];
const FRAMES = [...words.suggestions, words.suggestions[0]];
const MARKS = words.suggestions.map((suggestion) => ({ quote: suggestion.quote, tone: "ok" as const }));

function SliceNote() {
  return (
    <p className="m-0 mt-2.5 text-body leading-relaxed text-label">
      {highlightSegments(words.note, MARKS).map((segment, index) => {
        const frame = segment.tone ? words.suggestions.findIndex((suggestion) => suggestion.quote === segment.text) : -1;
        if (frame < 0) return <Fragment key={index}>{segment.text}</Fragment>;
        return (
          <span key={index} className={styles.mark} data-f={frame} style={cssVars({ "--f": frame })}>
            {segment.text}
          </span>
        );
      })}
    </p>
  );
}

function Decision() {
  return (
    <span className={styles.decision}>
      <span className={styles.key}>{ACCEPT_KEY}</span>
      <span className={styles.accepted}>
        <span className={styles.tick}>
          <CheckMark />
        </span>
        {words.accepted}
      </span>
    </span>
  );
}

function Frame({ suggestion, index }: { suggestion: Suggestion; index: number }) {
  return (
    <div className={styles.frame} data-f={index} style={cssVars({ "--f": index })}>
      <div className="flex items-center justify-between gap-3">
        <CodeChip code={suggestion.code} variant="new" />
        <Decision />
      </div>
      <p className="m-0 mt-2 truncate text-subhead font-semibold text-label">{suggestion.title}</p>
      <p className={`m-0 mt-0.5 truncate text-caption text-secondary ${styles.quote}`}>{suggestion.quote}</p>
    </div>
  );
}

export function HeroSlice() {
  return (
    <div aria-hidden="true" className={styles.slice} data-live="">
      <span className={styles.rings}>
        <span style={cssVars({ "--r": 0 })} />
        <span style={cssVars({ "--r": 1 })} />
        <span style={cssVars({ "--r": 2 })} />
      </span>
      <div className={styles.scene}>
        <span className={styles.ghost} />
        <span className={styles.level}>
          <CodeChange before={words.struck} after={words.adviceCode} addedLabel={words.addedLabel} changedLabel={words.changedLabel} />
        </span>
        <div className={styles.sheet}>
          <div className="flex items-center justify-between gap-3">
            <span className="text-caption font-semibold text-secondary">{words.noteLabel}</span>
            <span className={styles.live} />
          </div>
          <SliceNote />
        </div>
        <div className={styles.card}>
          <div className={styles.track}>
            {FRAMES.map((suggestion, index) => (
              <Frame key={`${suggestion.code}-${index}`} suggestion={suggestion} index={index} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
