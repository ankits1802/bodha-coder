import { ScrollStage } from "../motion/ScrollStage";
import { cssVars } from "../motion/cssVars";
import { LANDING_TEXT } from "../strings";
import styles from "./hero.module.css";
import { ProductWindow } from "./ProductWindow";

const PLACES = [
  { x: "-15%", y: "6%", depth: 0.95, time: "6.5s", tone: "ok" },
  { x: "-5%", y: "44%", depth: 0.5, time: "8s", tone: "ok" },
  { x: "-16%", y: "70%", depth: 0.8, time: "7.2s", tone: "low" },
  { x: "12%", y: "-14%", depth: 0.45, time: "9s", tone: "ok" },
  { x: "82%", y: "-15%", depth: 0.7, time: "7.6s", tone: "warn" },
  { x: "104%", y: "16%", depth: 1, time: "6.2s", tone: "ok" },
  { x: "96%", y: "52%", depth: 0.5, time: "8.8s", tone: "ok" },
  { x: "105%", y: "76%", depth: 0.85, time: "7s", tone: "warn" },
  { x: "58%", y: "-16%", depth: 0.4, time: "9.6s", tone: "ok" },
  { x: "33%", y: "-15%", depth: 0.65, time: "8.4s", tone: "low" },
] as const;

const DOT = { ok: styles.dotOk, warn: styles.dotWarn, low: styles.dotLow };

function CodeCloud() {
  return (
    <div aria-hidden="true" className={styles.cloud} data-live="">
      {LANDING_TEXT.floating.map((code, index) => {
        const place = PLACES[index % PLACES.length] ?? PLACES[0];
        return (
          <span
            key={code}
            className={styles.chip}
            style={cssVars({ "--x": place.x, "--y": place.y, "--d": place.depth, "--t": place.time, "--k": index, "--z": place.depth > 0.6 ? 3 : 0 })}
          >
            <span className={styles.chipBody}>
              <span className={`${styles.dot} ${DOT[place.tone]}`} />
              {code}
            </span>
          </span>
        );
      })}
    </div>
  );
}

export function FloatingProduct() {
  return (
    <section aria-label={LANDING_TEXT.product.label} className={styles.productSection}>
      <ScrollStage mode="enter" className={styles.stageWrap}>
        <div aria-hidden="true" className={styles.floor} data-live="" />
        <CodeCloud />
        <div className={styles.rise}>
          <div className={styles.stage}>
            <ProductWindow />
          </div>
        </div>
      </ScrollStage>
    </section>
  );
}
