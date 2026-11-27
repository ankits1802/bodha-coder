import { HighlightedText } from "@/components/shared/HighlightedText";
import { CodeChange } from "@/components/ui/CodeChange";
import { StatusDot } from "@/components/ui/StatusDot";
import { cssVars } from "../../motion/cssVars";
import { LANDING_TEXT } from "../../strings";
import styles from "./evidence.module.css";

const LINES = ["92%", "78%", "86%", "54%"];

export function EvidenceArt() {
  const words = LANDING_TEXT.bentoUi.evidence;
  const product = LANDING_TEXT.product;
  return (
    <div className={styles.board}>
      <div className={styles.note}>
        <span className={styles.beam} />
        <span className="text-caption font-semibold text-secondary">{product.noteLabel}</span>
        <HighlightedText text={words.note} marks={[{ quote: words.quote, tone: "ok" }]} className="mt-2.5 text-body-lg leading-relaxed" />
        <span className={styles.lines}>
          {LINES.map((width) => (
            <span key={width} className={styles.line} style={{ width }} />
          ))}
        </span>
      </div>
      <span className={styles.wire}>
        <span className={styles.pulse} />
      </span>
      <div className={styles.card}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CodeChange before={words.before} after={words.after} addedLabel={product.addedLabel} changedLabel={product.changedLabel} />
          <StatusDot tone="ok">{words.supported}</StatusDot>
        </div>
        <p className={styles.quote}>{words.quote}</p>
        <span className={styles.found}>
          <svg viewBox="0 0 16 16" className={styles.check}>
            <path d="M3.5 8.5l3 3 6-7" pathLength={1} />
          </svg>
          {words.found}
        </span>
      </div>
      <span className={styles.wire}>
        <span className={styles.pulse} style={cssVars({ "--lag": "1s" })} />
      </span>
      <span className={styles.codeSet}>
        <StatusDot tone="ok">{words.codeSet}</StatusDot>
      </span>
    </div>
  );
}
