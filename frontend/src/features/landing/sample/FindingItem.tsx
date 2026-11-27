import { shortcutKeys, type ShortcutId } from "@/components/shared/shortcuts/registry";
import { CheckMark } from "@/components/ui/CheckMark";
import { CodeChange } from "@/components/ui/CodeChange";
import { StatusDot } from "@/components/ui/StatusDot";
import type { Decision } from "./claim";
import styles from "./sample.module.css";
import type { SampleFinding } from "./samples";
import { SAMPLE_TEXT } from "./strings";
import type { SampleReview } from "./useSampleReview";

const CHOICES: readonly { decision: Decision; label: string; shortcut: ShortcutId }[] = [
  { decision: "accept", label: SAMPLE_TEXT.accept, shortcut: "acceptFinding" },
  { decision: "reject", label: SAMPLE_TEXT.reject, shortcut: "rejectFinding" },
];

interface FindingItemProps {
  finding: SampleFinding;
  decision: Decision | undefined;
  current: boolean;
  review: Pick<SampleReview, "point" | "choose" | "refAt">;
}

export function FindingItem({ finding, decision, current, review }: FindingItemProps) {
  return (
    <li
      data-finding={finding.key}
      data-decision={decision}
      aria-current={current || undefined}
      onFocus={() => review.point(finding.key)}
      onPointerDown={() => review.point(finding.key)}
      className={styles.finding}
    >
      <span className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <CodeChange before={finding.before} after={finding.after} addedLabel={SAMPLE_TEXT.addedLabel} changedLabel={SAMPLE_TEXT.changedLabel} />
        <StatusDot tone={finding.status.tone}>{finding.status.label}</StatusDot>
      </span>
      <span className="font-medium text-label">{finding.title}</span>
      <span className="text-callout text-secondary">{finding.reasoning}</span>
      <span className="sr-only">
        {SAMPLE_TEXT.evidence}
        {finding.evidence.map((quote) => (
          <q key={quote}> {quote}</q>
        ))}
      </span>
      <div role="group" aria-label={SAMPLE_TEXT.decisionFor(finding.after)} className="mt-1 flex flex-wrap gap-2">
        {CHOICES.map((choice) => {
          const keys = shortcutKeys(choice.shortcut, false);
          return (
            <button
              key={choice.decision}
              ref={choice.decision === "accept" ? review.refAt(finding.key) : undefined}
              type="button"
              aria-pressed={decision === choice.decision}
              aria-keyshortcuts={keys}
              data-choice={choice.decision}
              onClick={() => review.choose(finding.key, choice.decision)}
              className={styles.choice}
            >
              {choice.decision === "accept" ? <CheckMark className={styles.tick} /> : null}
              {choice.label}
              <kbd aria-hidden="true" className={styles.key}>
                {keys}
              </kbd>
            </button>
          );
        })}
      </div>
    </li>
  );
}
