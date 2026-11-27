import { CodeChange } from "@/components/ui/CodeChange";
import { StatusDot } from "@/components/ui/StatusDot";
import { cssVars } from "../../motion/cssVars";
import { LANDING_TEXT } from "../../strings";
import styles from "./compliance.module.css";
import { Screen } from "./Screen";
import screen from "./screen.module.css";

const MIX = [
  { practice: 0.18, cms: 0.3 },
  { practice: 0.42, cms: 0.86 },
  { practice: 0.7, cms: 0.62 },
  { practice: 0.96, cms: 0.22 },
] as const;

const product = LANDING_TEXT.product;

function LevelMix() {
  const words = LANDING_TEXT.deskUi.compliance;
  return (
    <div className={styles.chart}>
      <div className="flex items-center justify-between">
        <span className={screen.label}>{words.mix}</span>
        <span className="flex gap-3">
          <span className={styles.legend}>
            <span className={`${styles.swatch} ${styles.provider}`} />
            {words.provider}
          </span>
          <span className={styles.legend}>
            <span className={`${styles.swatch} ${styles.benchmark}`} />
            {words.cms}
          </span>
        </span>
      </div>
      <div className={styles.bars}>
        {MIX.map((level, index) => (
          <div key={words.levels[index]} className={styles.column}>
            <span className={styles.slot}>
              <span className={`${styles.bar} ${styles.provider}`} style={cssVars({ "--h": level.practice, "--i": index })} />
              <span className={`${styles.bar} ${styles.benchmark}`} style={cssVars({ "--h": level.cms, "--i": index })} />
            </span>
            <span className={styles.level}>{words.levels[index]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ComplianceUi() {
  const words = LANDING_TEXT.deskUi.compliance;
  return (
    <Screen title={words.title}>
      <div className={styles.case}>
        <CodeChange before={words.billed} after={words.documented} addedLabel={product.addedLabel} changedLabel={product.changedLabel} />
        <StatusDot tone="bad">{words.verdict}</StatusDot>
      </div>
      {words.checks.map((check, index) => (
        <div key={check} className={styles.check} style={cssVars({ "--i": index })}>
          <StatusDot tone="warn">{check}</StatusDot>
        </div>
      ))}
      <LevelMix />
    </Screen>
  );
}
