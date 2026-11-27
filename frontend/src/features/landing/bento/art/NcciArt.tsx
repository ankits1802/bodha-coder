import { StatusDot } from "@/components/ui/StatusDot";
import { LANDING_TEXT } from "../../strings";
import styles from "./ncci.module.css";

export function NcciArt() {
  const words = LANDING_TEXT.bentoUi.ncci;
  return (
    <div className={styles.stack}>
      <div className={styles.card}>
        <div className={styles.pair}>
          <span className={`${styles.chip} ${styles.left}`}>{words.first}</span>
          <span className={styles.spark} />
          <span className={`${styles.chip} ${styles.right}`}>{words.second}</span>
        </div>
        <div className="mt-3 flex flex-col items-center gap-1">
          <StatusDot tone="bad">{words.together}</StatusDot>
          <span className="text-caption text-secondary">{words.modifier}</span>
        </div>
      </div>
      <div className={`${styles.card} ${styles.units}`}>
        <span className={styles.unitChip}>{words.units}</span>
        <StatusDot tone="bad">{words.over}</StatusDot>
      </div>
    </div>
  );
}
