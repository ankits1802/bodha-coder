import { cssVars } from "../motion/cssVars";
import { LANDING_TEXT } from "../strings";
import styles from "./story.module.css";

const HEIGHT = 300;
const PHRASE_END = 214;
const CODE_START = 300;

function phraseY(index: number): number {
  return 70 + index * 80;
}

function codeY(index: number): number {
  return 96 + index * 54;
}

function wire(index: number): string {
  const middle = (PHRASE_END + CODE_START) / 2;
  const from = phraseY(index);
  const to = codeY(index);
  return `M ${PHRASE_END} ${from} C ${middle} ${from}, ${middle} ${to}, ${CODE_START} ${to}`;
}

function top(y: number): string {
  return `${(y / HEIGHT) * 100}%`;
}

export function ReviewVisual() {
  const items = LANDING_TEXT.story.review;
  return (
    <div data-index={1} className={styles.visual}>
      <div className={styles.board}>
        <svg viewBox={`0 0 440 ${HEIGHT}`} className={styles.wires}>
          {items.map((item, index) => (
            <path key={item.code} d={wire(index)} pathLength={1} className={styles.wire} style={cssVars({ "--n": index })} />
          ))}
        </svg>
        {items.map((item, index) => (
          <span
            key={item.phrase}
            className={`${styles.phrase} ${styles[`tone-${item.tone}`]}`}
            style={cssVars({ "--n": index, "--top": top(phraseY(index)) })}
          >
            <span className={styles.ink}>{item.phrase}</span>
          </span>
        ))}
        {items.map((item, index) => (
          <span
            key={item.code}
            className={`${styles.code} ${styles[`tone-${item.tone}`]}`}
            style={cssVars({ "--n": index, "--top": top(codeY(index)) })}
          >
            <span className={styles.codeDot} />
            {item.code}
          </span>
        ))}
      </div>
    </div>
  );
}
