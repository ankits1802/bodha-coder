"use client";

import { StatusDot } from "@/components/ui/StatusDot";
import { ClaimSummary, CodeLine } from "./ClaimLines";
import { FindingItem } from "./FindingItem";
import styles from "./sample.module.css";
import { SampleNoteText } from "./SampleNoteText";
import type { SampleNote } from "./samples";
import { SAMPLE_TEXT } from "./strings";
import { useSampleReview } from "./useSampleReview";

interface SamplePanelProps {
  sample: SampleNote;
  id: string;
  labelledBy: string;
  hidden: boolean;
}

export function SamplePanel({ sample, id, labelledBy, hidden }: SamplePanelProps) {
  const review = useSampleReview(sample);
  const focused = sample.findings.find((finding) => finding.key === review.current);
  const shown = focused ? [focused] : sample.findings.filter((finding) => review.decisions[finding.key] === "accept");
  return (
    <div id={id} role="tabpanel" aria-labelledby={labelledBy} tabIndex={0} hidden={hidden} onKeyDown={review.onKeyDown} className={styles.panel}>
      <div className={styles.window}>
        <SampleNoteText header={sample.header} note={sample.note} shown={shown} />
        <div className="flex min-w-0 flex-col">
          <div className="flex flex-col gap-3 px-5 pt-6 pb-4 sm:px-6">
            <StatusDot tone={sample.verdict.tone}>{sample.verdict.label}</StatusDot>
            <CodeLine label={SAMPLE_TEXT.billed} codes={sample.billed} />
          </div>
          <ul aria-label={SAMPLE_TEXT.findings} className="m-0 list-none p-0">
            {sample.findings.map((finding) => (
              <FindingItem
                key={finding.key}
                finding={finding}
                decision={review.decisions[finding.key]}
                current={review.current === finding.key}
                review={review}
              />
            ))}
          </ul>
          <ClaimSummary sample={sample} decisions={review.decisions} />
        </div>
      </div>
    </div>
  );
}
