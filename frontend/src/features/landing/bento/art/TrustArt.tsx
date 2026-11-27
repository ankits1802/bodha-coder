import { cssVars } from "../../motion/cssVars";
import { LANDING_TEXT } from "../../strings";
import styles from "./trust.module.css";

const NOTES = 10;
const HELD = 6;

function Person() {
  return (
    <svg viewBox="0 0 16 16" className={styles.person}>
      <circle cx="8" cy="5.5" r="2.6" />
      <path d="M3.2 13.5c.6-2.5 2.5-3.9 4.8-3.9s4.2 1.4 4.8 3.9" />
    </svg>
  );
}

function Tick() {
  return (
    <svg viewBox="0 0 16 16" className={styles.tick}>
      <path d="M4.2 8.4l2.5 2.5 5-5.6" />
    </svg>
  );
}

export function TrustArt() {
  const words = LANDING_TEXT.bentoUi.trust;
  return (
    <div className={styles.wrap}>
      <div className={styles.meter}>
        <span className={styles.label}>{words.interval}</span>
        <div className={styles.track}>
          <span className={styles.band} />
          <span className={styles.point} />
          <span className={styles.threshold}>
            <span className={styles.thresholdLabel}>{words.bar}</span>
          </span>
        </div>
      </div>
      <div className={styles.notes}>
        {Array.from({ length: NOTES }, (_, index) => (
          <span key={index} className={index === HELD ? styles.held : styles.auto} style={cssVars({ "--i": index })}>
            {index === HELD ? <Person /> : <Tick />}
          </span>
        ))}
      </div>
      <div className={styles.legend}>
        <span className={styles.key}>
          <span className={`${styles.swatch} ${styles.swatchAuto}`} />
          {words.auto}
        </span>
        <span className={styles.key}>
          <span className={`${styles.swatch} ${styles.swatchHeld}`} />
          {words.held}
        </span>
      </div>
    </div>
  );
}
