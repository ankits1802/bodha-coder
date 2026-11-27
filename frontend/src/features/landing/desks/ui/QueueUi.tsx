import { CodeChip } from "@/components/ui/CodeChip";
import { StatusDot } from "@/components/ui/StatusDot";
import { cssVars } from "../../motion/cssVars";
import { LANDING_TEXT } from "../../strings";
import styles from "./queue.module.css";
import { Screen } from "./Screen";
import screen from "./screen.module.css";

function Footer() {
  const words = LANDING_TEXT.deskUi.queue;
  return (
    <div className={styles.foot}>
      <span className="flex gap-1.5">
        {words.keys.map((key, index) => (
          <kbd key={key} className={styles.key} style={cssVars({ "--k": index })}>
            {key}
          </kbd>
        ))}
      </span>
      <span className={screen.pill}>{words.approve}</span>
    </div>
  );
}

export function QueueUi() {
  const words = LANDING_TEXT.deskUi.queue;
  const columns = words.columns;
  return (
    <Screen title={words.title}>
      <div className={`${styles.grid} ${styles.head}`}>
        <span>{columns.visit}</span>
        <span>{columns.billed}</span>
        <span>{columns.bodha}</span>
        <span>{columns.status}</span>
      </div>
      <div className={styles.body}>
        <span className={styles.cursor} />
        {words.rows.map((row, index) => {
          const changed = row.billed !== row.bodha;
          return (
            <div key={row.visit} className={`${styles.grid} ${styles.row}`} style={cssVars({ "--i": index })}>
              <span className="text-secondary tabular-nums">{row.visit}</span>
              <span>
                <CodeChip code={row.billed} variant={changed ? "old" : "default"} />
              </span>
              <span>
                <CodeChip code={row.bodha} variant={changed ? "new" : "default"} />
              </span>
              <StatusDot tone={row.tone}>{row.status}</StatusDot>
            </div>
          );
        })}
      </div>
      <Footer />
    </Screen>
  );
}
