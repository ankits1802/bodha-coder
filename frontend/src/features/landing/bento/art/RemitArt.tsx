import { StatusDot } from "@/components/ui/StatusDot";
import { LANDING_TEXT } from "../../strings";
import styles from "./remit.module.css";

function Connector() {
  return (
    <span className={styles.link}>
      <span className={styles.dot} />
    </span>
  );
}

export function RemitArt() {
  const words = LANDING_TEXT.bentoUi.remit;
  return (
    <div className={styles.loop}>
      <div className={styles.file}>
        <span className={styles.fold} />
        <span className={styles.fileName}>{words.file}</span>
      </div>
      <Connector />
      <div className={styles.card}>
        <span className="text-subhead font-semibold tabular-nums">{words.line}</span>
        <span className={styles.flag}>
          <StatusDot tone="warn">{words.status}</StatusDot>
        </span>
      </div>
      <Connector />
      <div className={styles.card}>
        <span className={styles.letter}>
          <span />
          <span />
          <span />
        </span>
        <span className="text-subhead font-semibold">{words.letter}</span>
        <span className="text-caption text-secondary">{words.appeal}</span>
      </div>
    </div>
  );
}
