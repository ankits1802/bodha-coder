import { Fragment } from "react";
import { highlightSegments, type HighlightTone, type Mark } from "@/lib/highlight";

const TONES: Record<HighlightTone, string> = {
  ok: "hl-ok",
  warn: "hl-warn",
  bad: "hl-bad",
};

interface HighlightedTextProps {
  text: string;
  marks: Mark[];
  className?: string;
}

export function HighlightedText({ text, marks, className = "" }: HighlightedTextProps) {
  const segments = highlightSegments(text, marks);
  return (
    <p className={`m-0 whitespace-pre-wrap break-words ${className}`}>
      {segments.map((segment, index) =>
        segment.tone ? (
          <mark key={index} className={`text-label ${TONES[segment.tone]}`}>
            {segment.text}
          </mark>
        ) : (
          <Fragment key={index}>{segment.text}</Fragment>
        ),
      )}
    </p>
  );
}
