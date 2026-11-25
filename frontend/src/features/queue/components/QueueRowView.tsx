import Link from "next/link";
import { CodeList } from "@/components/shared/CodeList";
import { noteStatus } from "@/components/shared/noteStatus";
import { StatusDot } from "@/components/ui/StatusDot";
import { TextButton } from "@/components/ui/TextButton";
import { Td, Tr } from "@/components/ui/Table";
import type { Lane, QueueRow } from "@/lib/api/types";
import { formatDueIn } from "@/lib/format";
import { canOpen, isAwaitingProvider, isSelectable, noteHref, patientName } from "../queueRules";
import { QUEUE_TEXT } from "../strings";

export interface RowControls {
  lane: Lane | undefined;
  selectable: boolean;
  canRemind: boolean;
  remindingId: string | null;
  onToggle: (noteId: string) => void;
  onRemind: (noteId: string) => void;
}

function SelectCell({ row, selected, controls }: { row: QueueRow; selected: boolean; controls: RowControls }) {
  const name = patientName(row);
  if (isSelectable(row)) {
    return (
      <input
        type="checkbox"
        className="size-4 accent-label"
        checked={selected}
        aria-label={QUEUE_TEXT.selectRow(name)}
        onChange={() => controls.onToggle(row.id)}
      />
    );
  }
  if (row.status === "queued" || row.status === "reading") {
    return <input type="checkbox" className="size-4 accent-label" disabled aria-label={QUEUE_TEXT.stillReading(name)} />;
  }
  return null;
}

function StatusCell({ row, controls }: { row: QueueRow; controls: RowControls }) {
  const status = noteStatus(row);
  const remindable = controls.canRemind && isAwaitingProvider(row);
  return (
    <span className="flex items-center gap-2.5">
      <StatusDot tone={status.tone}>{status.label}</StatusDot>
      {remindable ? (
        <TextButton
          className="text-subhead"
          aria-label={QUEUE_TEXT.remindLabel(patientName(row))}
          disabled={controls.remindingId === row.id}
          aria-busy={controls.remindingId === row.id || undefined}
          onClick={() => controls.onRemind(row.id)}
        >
          {QUEUE_TEXT.remind}
        </TextButton>
      ) : null}
    </span>
  );
}

export function QueueRowView({ row, selected, controls }: { row: QueueRow; selected: boolean; controls: RowControls }) {
  const due = formatDueIn(row.due_at);
  return (
    <Tr selected={selected}>
      {controls.selectable ? (
        <Td className="w-4">
          <SelectCell row={row} selected={selected} controls={controls} />
        </Td>
      ) : null}
      <Td>
        {canOpen(row) ? (
          <Link href={noteHref(row.id, controls.lane)} className="font-medium hover:underline">
            {patientName(row)}
          </Link>
        ) : (
          <span className="text-secondary">{patientName(row)}</span>
        )}
      </Td>
      <Td className="text-secondary">{row.provider_name}</Td>
      <Td>
        <CodeList codes={row.billed} max={3} />
      </Td>
      <Td>
        <CodeList codes={row.suggested} max={2} />
      </Td>
      <Td>
        <StatusCell row={row} controls={controls} />
      </Td>
      <Td className={`text-right whitespace-nowrap tabular-nums ${due.overdue ? "text-bad-text" : "text-secondary"}`}>
        {due.text}
      </Td>
    </Tr>
  );
}
