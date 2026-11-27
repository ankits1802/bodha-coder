import { CodeChange } from "@/components/ui/CodeChange";
import { CodeChip } from "@/components/ui/CodeChip";
import { StatusDot } from "@/components/ui/StatusDot";
import { cssVars } from "../../motion/cssVars";
import { LANDING_TEXT } from "../../strings";
import styles from "./billing.module.css";
import { Screen } from "./Screen";
import screen from "./screen.module.css";

const product = LANDING_TEXT.product;

function RemitPanel() {
  const words = LANDING_TEXT.deskUi.billing;
  return (
    <div className={styles.remit}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-2">
          <span className={screen.softPill}>{words.remit}</span>
          <CodeChange before={words.billed} after={words.paid} addedLabel={product.addedLabel} changedLabel={product.changedLabel} />
        </span>
        <span className={styles.flag}>
          <StatusDot tone="warn">{words.status}</StatusDot>
        </span>
      </div>
      <div className="mt-3 flex items-center justify-between gap-2">
        <span className="text-footnote text-secondary">{words.appeal}</span>
        <span className={screen.softPill}>{words.draft}</span>
      </div>
    </div>
  );
}

export function BillingUi() {
  const words = LANDING_TEXT.deskUi.billing;
  const columns = words.columns;
  return (
    <Screen title={words.title} aside={<span className={screen.softPill}>{words.format}</span>}>
      <div className={`${styles.grid} ${styles.head}`}>
        <span>{columns.code}</span>
        <span>{columns.pointers}</span>
        <span className="text-right">{columns.units}</span>
      </div>
      {words.lines.map((line, index) => (
        <div key={line.code} className={`${styles.grid} ${styles.line}`} style={cssVars({ "--i": index })}>
          <span>
            <CodeChip code={line.code} />
          </span>
          <span className="font-semibold tracking-wide">{line.pointers}</span>
          <span className="text-right tabular-nums">{line.units}</span>
        </div>
      ))}
      <div className={styles.export}>
        <span className={styles.file}>
          <span className={styles.fileBody}>{words.file}</span>
        </span>
        <span className={`${screen.pill} ${styles.button}`}>{words.export}</span>
      </div>
      <RemitPanel />
    </Screen>
  );
}
