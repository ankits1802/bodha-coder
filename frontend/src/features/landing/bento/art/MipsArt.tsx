import { CodeChip } from "@/components/ui/CodeChip";
import { StatusDot } from "@/components/ui/StatusDot";
import { cssVars } from "../../motion/cssVars";
import { LANDING_TEXT } from "../../strings";
import styles from "./mips.module.css";

export function MipsArt() {
  const measures = LANDING_TEXT.bentoUi.mips;
  return (
    <div className={styles.stack}>
      {measures.map((measure, index) => (
        <div key={measure.id} className={styles.card} style={cssVars({ "--i": index })}>
          <span className={styles.badge}>{measure.id}</span>
          <span className="flex min-w-0 flex-1 flex-col gap-1.5">
            <span className="text-subhead font-semibold">{measure.name}</span>
            <span className="flex flex-wrap items-center gap-2">
              {measure.code ? (
                <span className={styles.code}>
                  <CodeChip code={measure.code} variant="new" />
                </span>
              ) : (
                <span className={styles.slot} />
              )}
              <StatusDot tone={measure.tone}>{measure.status}</StatusDot>
            </span>
          </span>
        </div>
      ))}
    </div>
  );
}
