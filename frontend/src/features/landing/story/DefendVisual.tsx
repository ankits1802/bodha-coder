import { cssVars } from "../motion/cssVars";
import { LANDING_TEXT } from "../strings";
import styles from "./story.module.css";

const SHEETS = [
  { n: 2, r: "14deg", x: "46%" },
  { n: 1, r: "-12deg", x: "-44%" },
  { n: 0, r: "-2deg", x: "0%" },
] as const;

function Seal() {
  return (
    <svg viewBox="0 0 64 64" className={styles.seal}>
      <circle cx="32" cy="32" r="28" pathLength={1} className={styles.sealRing} />
      <path d="M20 33 l8 8 l16 -18" pathLength={1} className={styles.sealCheck} />
    </svg>
  );
}

export function DefendVisual() {
  const words = LANDING_TEXT.story.defend;
  return (
    <div data-index={2} className={styles.visual}>
      <div className={styles.packet}>
        {SHEETS.map((sheet) => (
          <div key={sheet.n} className={styles.sheet} style={cssVars({ "--n": sheet.n, "--r": sheet.r, "--x": sheet.x })}>
            {sheet.n === 0 ? <span className={styles.sheetTitle}>{words.packet}</span> : null}
            <span className={styles.line} style={cssVars({ "--w": "70%" })} />
            <span className={styles.line} style={cssVars({ "--w": "86%" })} />
            <span className={styles.line} style={cssVars({ "--w": "58%" })} />
          </div>
        ))}
        <Seal />
        <div className={styles.addendum}>
          <span className={styles.addendumDot} />
          {words.addendum}
          <span className={styles.signed}>{words.signed}</span>
        </div>
      </div>
    </div>
  );
}
