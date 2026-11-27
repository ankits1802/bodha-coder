import { HighlightedText } from "@/components/shared/HighlightedText";
import styles from "./sample.module.css";
import type { SampleFinding } from "./samples";
import { SAMPLE_TEXT } from "./strings";

const LABELS = { start: SAMPLE_TEXT.evidence, end: SAMPLE_TEXT.evidenceEnd };

interface SampleNoteTextProps {
  header: string;
  note: string;
  shown: readonly SampleFinding[];
}

export function SampleNoteText({ header, note, shown }: SampleNoteTextProps) {
  const marks = shown.flatMap((finding) => finding.evidence.map((quote) => ({ quote, tone: "ok" as const })));
  return (
    <div className={styles.note}>
      <span className="text-caption font-semibold text-secondary">{header}</span>
      <HighlightedText
        key={shown.map((finding) => finding.key).join(" ")}
        text={note}
        marks={marks}
        labels={LABELS}
        className="mt-3 text-body-lg leading-relaxed text-label"
      />
    </div>
  );
}
