import { Fragment } from "react";
import { highlightSegments, type HighlightTone, type Mark } from "@/lib/highlight";

const TONES: Record<HighlightTone, string> = {
  ok: "hl-ok",
  warn: "hl-warn",
  bad: "hl-bad",
};

export interface MarkLabels {
  start: string;
  end: string;
}

interface HighlightedTextProps {
  text: string;
  marks: Mark[];
  labels?: MarkLabels;
  className?: string;
}

export function HighlightedText({ text, marks, labels, className = "" }: HighlightedTextProps) {
  const segments = highlightSegments(text, marks);
  return (
    <p className={`m-0 whitespace-pre-wrap break-words ${className}`}>
      {segments.map((segment, index) =>
        segment.tone ? (
          <mark key={index} className={`text-label ${TONES[segment.tone]}`}>
            {labels ? <span className="sr-only">{`${labels.start} `}</span> : null}
            {segment.text}
            {labels ? <span className="sr-only">{` ${labels.end}`}</span> : null}
          </mark>
        ) : (
          <Fragment key={index}>{segment.text}</Fragment>
        ),
      )}
    </p>
  );
}
