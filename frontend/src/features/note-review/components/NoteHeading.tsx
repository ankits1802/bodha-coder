import { StatusDot } from "@/components/ui/StatusDot";
import type { NoteHeader } from "@/lib/api/types";
import { formatCalendarDay, formatDueIn } from "@/lib/format";
import { REVIEW_TEXT } from "../strings";

interface NoteHeadingProps {
  note: NoteHeader;
  placeLabel: string;
}

export function NoteHeading({ note, placeLabel }: NoteHeadingProps) {
  const due = formatDueIn(note.due_at);
  const parts = [
    REVIEW_TEXT.ageSex(note.patient_age, note.patient_sex),
    REVIEW_TEXT.seen(formatCalendarDay(note.service_date, "long")),
    `${note.provider.name}, ${note.provider.credential}`,
    placeLabel,
    note.visit_type,
  ].filter(Boolean);
  return (
    <header>
      <h1 className="m-0 text-large-title font-bold tracking-title">{note.patient_name ?? REVIEW_TEXT.patientUnknown}</h1>
      <p className="mt-0.5 mb-0 flex flex-wrap items-center gap-x-1.5 text-body-lg text-secondary">
        <span>{parts.join(" · ")}</span>
        {note.status === "ready" ? (
          <>
            <span aria-hidden="true">·</span>
            <StatusDot tone={due.overdue ? "bad" : "warn"} className="text-body-lg text-secondary">
              {due.overdue ? REVIEW_TEXT.overdue : REVIEW_TEXT.due(due.text)}
            </StatusDot>
          </>
        ) : null}
      </p>
    </header>
  );
}
