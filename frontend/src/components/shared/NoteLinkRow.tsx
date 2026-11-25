import Link from "next/link";
import type { ReactNode } from "react";
import { Chevron } from "@/components/ui/Chevron";
import { StatusDot } from "@/components/ui/StatusDot";
import type { Lane, QueueRow } from "@/lib/api/types";
import { formatCalendarDay, formatDueIn } from "@/lib/format";
import { noteStatus } from "./noteStatus";
import { SHARED_TEXT } from "./strings";

interface NoteLinkRowProps {
  row: QueueRow;
  lane: Lane;
  codes?: ReactNode;
}

export function NoteLinkRow({ row, lane, codes }: NoteLinkRowProps) {
  const status = noteStatus(row);
  const words = SHARED_TEXT.noteRow;
  return (
    <li>
      <Link
        href={`/notes/${encodeURIComponent(row.id)}?lane=${lane}`}
        className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4.5 py-3.5 hover:bg-row-hover"
      >
        <span className="flex min-w-0 flex-1 basis-48 flex-col gap-0.5">
          <span className="truncate text-body-lg font-semibold">{row.patient_name ?? row.file_name}</span>
          <span className="text-subhead text-secondary">{words.meta(row.provider_name, formatCalendarDay(row.service_date))}</span>
        </span>
        {codes}
        <StatusDot tone={status.tone} className="sm:w-37.5">
          {status.label}
        </StatusDot>
        <span className="w-11 text-right text-subhead text-secondary tabular-nums">
          <span className="sr-only">{words.dueIn} </span>
          {formatDueIn(row.due_at).text}
        </span>
        <Chevron />
      </Link>
    </li>
  );
}
