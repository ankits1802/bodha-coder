import { HighlightedText } from "@/components/shared/HighlightedText";
import { CodeChange } from "@/components/ui/CodeChange";
import { StatusDot } from "@/components/ui/StatusDot";
import { cssVars } from "../motion/cssVars";
import { LANDING_TEXT } from "../strings";
import { EvidenceSwitch } from "./EvidenceSwitch";
import styles from "./hero.module.css";

const words = LANDING_TEXT.product;

function WindowBar() {
  return (
    <div className="grid h-11 grid-cols-[1fr_auto_1fr] items-center gap-3 border-b border-hairline px-4">
      <div aria-hidden="true" className="flex gap-2">
        <span className="size-2.75 rounded-full bg-separator" />
        <span className="size-2.75 rounded-full bg-separator" />
        <span className="size-2.75 rounded-full bg-separator" />
      </div>
      <span className="text-caption font-semibold text-secondary">{words.window}</span>
      <div className="flex justify-end">
        <EvidenceSwitch label={words.evidence} />
      </div>
    </div>
  );
}

function Verdict() {
  return (
    <div className={`px-5 pt-6 pb-4.5 ${styles.verdict}`}>
      <StatusDot tone="bad">{words.verdict}</StatusDot>
      <p className="mt-1.5 mb-0 text-title font-semibold tracking-headline">
        {words.adviceLead}
        <span className={styles.newCode}>{words.adviceCode}</span>
        {words.adviceTail}
        <span className={styles.struck}>{words.struck}</span>
      </p>
    </div>
  );
}

export function ProductWindow() {
  return (
    <div className={styles.window} data-evidence="on">
      <WindowBar />
      <div className="flex flex-wrap">
        <div className={`min-w-0 flex-[1_1_23rem] border-r border-hairline px-7 pt-7 pb-8 ${styles.note}`}>
          <span aria-hidden="true" className={styles.beam} />
          <span className="text-caption font-semibold text-tertiary">{words.noteLabel}</span>
          <HighlightedText text={words.note} marks={[...words.marks]} className="mt-2.5 text-body leading-relaxed" />
        </div>
        <div className="min-w-0 flex-[1_1_23rem]">
          <Verdict />
          <ul className="m-0 list-none p-0">
            {words.rows.map((row, index) => (
              <li
                key={row.before}
                className={`flex items-center justify-between gap-3 border-t border-hairline px-5 py-3.25 ${styles.row}`}
                style={cssVars({ "--i": index })}
              >
                <CodeChange before={row.before} after={row.after} addedLabel={words.addedLabel} changedLabel={words.changedLabel} />
                <StatusDot tone={row.tone}>{row.status}</StatusDot>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
