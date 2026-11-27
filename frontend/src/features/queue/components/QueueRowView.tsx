import Link from "next/link";
import { CodeList } from "@/components/shared/CodeList";
import { noteStatus } from "@/components/shared/noteStatus";
import { StatusDot } from "@/components/ui/StatusDot";
import { TextButton } from "@/components/ui/TextButton";
import { Td, Tr } from "@/components/ui/Table";
import type { Lane, LaneReason, QueueRow } from "@/lib/api/types";
import { formatDueIn, formatMoneyChange } from "@/lib/format";
import { NOTE_ROW_ATTRIBUTE, canOpen, isAwaitingProvider, isSelectable, noteHref, patientName, type Member } from "../queueRules";
import { QUEUE_TEXT } from "../strings";
import { AssigneeChip } from "./AssigneeChip";

export interface RowControls {
  lane: Lane | undefined;
  reason: LaneReason | undefined;
  member: Member;
  selectable: boolean;
  canRemind: boolean;
  remindingId: string | null;
  onToggle: (noteId: string) => void;
  onRemind: (noteId: string) => void;
}

function SelectCell({ row, selected, controls }: { row: QueueRow; selected: boolean; controls: RowControls }) {
  const name = patientName(row);
  if (isSelectable(row, controls.member)) {
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

function ImpactLine({ cents }: { cents: number | null }) {
  if (cents === null) return null;
  return (
    <span className="mt-0.5 block text-footnote text-secondary tabular-nums">
      <span className="sr-only">{QUEUE_TEXT.impact} </span>
      {formatMoneyChange(cents / 100)}
    </span>
  );
}

export function QueueRowView({ row, selected, controls }: { row: QueueRow; selected: boolean; controls: RowControls }) {
  const due = formatDueIn(row.due_at);
  return (
    <Tr selected={selected} {...{ [NOTE_ROW_ATTRIBUTE]: row.id }}>
      {controls.selectable ? (
        <Td className="w-4">
          <SelectCell row={row} selected={selected} controls={controls} />
        </Td>
      ) : null}
      <Td>
        {canOpen(row) ? (
          <Link href={noteHref(row.id, controls.lane, controls.reason)} className="font-medium hover:underline">
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
        <ImpactLine cents={row.impact_cents} />
      </Td>
      <Td>
        <StatusCell row={row} controls={controls} />
      </Td>
      <Td className="w-12">
        <AssigneeChip name={row.assignee_name} />
      </Td>
      <Td className={`text-right whitespace-nowrap tabular-nums ${due.overdue ? "text-bad-text" : "text-secondary"}`}>
        {due.text}
      </Td>
    </Tr>
  );
}
