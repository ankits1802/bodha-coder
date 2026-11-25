import { HighlightedText } from "@/components/shared/HighlightedText";
import { Panel } from "@/components/ui/Panel";
import type { Finding, NoteText } from "@/lib/api/types";
import { formatInstantDay } from "@/lib/format";
import { marksFor } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { NoteLegend } from "./NoteLegend";

interface NotePanelProps {
  texts: NoteText[];
  findings: Finding[];
}

function TextBlock({ text, marks }: { text: NoteText; marks: ReturnType<typeof marksFor> }) {
  if (text.source === "document") return <HighlightedText text={text.text} marks={marks} />;
  return (
    <div className="rounded-field bg-chip px-4 py-3.5">
      <h3 className="m-0 mb-1 font-sans text-caption font-semibold text-tertiary">
        {REVIEW_TEXT.addendumHeading(formatInstantDay(text.created_at))}
      </h3>
      <HighlightedText text={text.text} marks={marks} />
    </div>
  );
}

export function NotePanel({ texts, findings }: NotePanelProps) {
  const marks = marksFor(findings);
  const ordered = [...texts].sort((a, b) => a.revision - b.revision);
  return (
    <Panel aria-label={REVIEW_TEXT.notePanel} className="min-w-0 flex-[1_1_31rem]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hairline px-5 py-3.5">
        <h2 className="m-0 font-sans text-body-lg font-semibold">{REVIEW_TEXT.notePanel}</h2>
        <NoteLegend />
      </div>
      <article className="flex flex-col gap-5 px-6.5 pt-5.5 pb-7 text-body-lg leading-relaxed">
        {ordered.length === 0 ? <p className="m-0 text-secondary">{REVIEW_TEXT.noText}</p> : null}
        {ordered.map((text) => (
          <TextBlock key={text.revision} text={text} marks={marks} />
        ))}
      </article>
    </Panel>
  );
}
