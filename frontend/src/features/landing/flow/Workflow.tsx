import { SECTION_IDS } from "../anchors";
import { ScrollStage } from "../motion/ScrollStage";
import { cssVars } from "../motion/cssVars";
import { LANDING_TEXT } from "../strings";
import styles from "./flow.module.css";
import { FlowIcon } from "./FlowIcon";

export function Workflow() {
  const words = LANDING_TEXT.flow;
  return (
    <section id={SECTION_IDS.flow} aria-labelledby="flow-title" className={styles.section}>
      <div className="relative mx-auto max-w-landing">
        <h2 id="flow-title" data-reveal="" className="m-0 font-display text-hero-sm font-bold tracking-display text-white sm:text-display">
          {words.title}
        </h2>
        <p data-reveal="" className={styles.lead}>
          {words.lead}
        </p>
        <ScrollStage mode="through" className={styles.stage}>
          <span aria-hidden="true" className={styles.track}>
            <span className={styles.fill} />
          </span>
          <ol className={styles.steps}>
            {words.steps.map((step, index) => (
              <li key={step.key} className={styles.step} style={cssVars({ "--i": index })}>
                <span aria-hidden="true" className={styles.node}>
                  <FlowIcon step={step.key} className={styles.icon} />
                  <span className={styles.lit}>
                    <FlowIcon step={step.key} className={styles.icon} />
                  </span>
                </span>
                <h3 className={styles.title}>{step.title}</h3>
                <p className={styles.body}>{step.body}</p>
              </li>
            ))}
          </ol>
        </ScrollStage>
      </div>
    </section>
  );
}
