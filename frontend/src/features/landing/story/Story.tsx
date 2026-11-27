import { ScrollStage } from "../motion/ScrollStage";
import { LANDING_TEXT } from "../strings";
import styles from "./story.module.css";
import { DefendVisual } from "./DefendVisual";
import { ReviewVisual } from "./ReviewVisual";
import { UploadVisual } from "./UploadVisual";

export function Story() {
  const words = LANDING_TEXT.story;
  return (
    <section id="how" aria-label={words.label} className="scroll-mt-16">
      <ScrollStage mode="pin" acts={words.acts.length} className={styles.track}>
        <div className={styles.sticky}>
          <h2 className={`font-display ${styles.steps}`}>
            {words.acts.map((act, index) => (
              <span key={act.step} data-index={index} className={styles.step}>
                {act.step}{" "}
              </span>
            ))}
          </h2>
          <span aria-hidden="true" className={styles.progress}>
            <span className={styles.progressFill} />
          </span>
          <div className={styles.body}>
            <ol className={styles.acts}>
              {words.acts.map((act, index) => (
                <li key={act.title} data-index={index} className={styles.act}>
                  <h3 className="m-0 font-display text-large-title font-bold tracking-title sm:text-display">{act.title}</h3>
                  <p className="mt-4 mb-0 max-w-110 text-title3 text-secondary">{act.body}</p>
                </li>
              ))}
            </ol>
            <div aria-hidden="true" className={styles.visuals}>
              <UploadVisual />
              <ReviewVisual />
              <DefendVisual />
            </div>
          </div>
        </div>
      </ScrollStage>
    </section>
  );
}
