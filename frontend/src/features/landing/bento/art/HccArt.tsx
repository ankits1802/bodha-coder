import { CodeChip } from "@/components/ui/CodeChip";
import { StatusDot } from "@/components/ui/StatusDot";
import { cssVars } from "../../motion/cssVars";
import { LANDING_TEXT } from "../../strings";
import styles from "./hcc.module.css";

export function HccArt() {
  const rows = LANDING_TEXT.bentoUi.hcc;
  return (
    <div className={styles.panel}>
      <span className={styles.sweep} />
      <ul className={styles.list}>
        {rows.map((row, index) => (
          <li key={row.code} className={styles.row} style={cssVars({ "--i": index })}>
            <span className="flex items-center gap-2">
              <CodeChip code={row.code} />
              <span className="text-caption font-semibold text-secondary">{row.hcc}</span>
            </span>
            <StatusDot tone={row.tone}>{row.status}</StatusDot>
          </li>
        ))}
      </ul>
    </div>
  );
}
