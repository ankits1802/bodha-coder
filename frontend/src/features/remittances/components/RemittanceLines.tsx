import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { RemittanceLine } from "@/lib/api/types";
import { FORMAT_WORDS, formatCalendarDay } from "@/lib/format";
import { STATUS_TONES, canAppeal, formatCents } from "../remittanceModel";
import { REMITTANCE_TEXT } from "../strings";

interface RemittanceLinesProps {
  lines: RemittanceLine[];
  onDraft: (lineId: string) => void;
}

function PatientCell({ line }: { line: RemittanceLine }) {
  const name = line.patient_name ?? line.claim_ref ?? FORMAT_WORDS.empty;
  if (!line.note_id) return <span className="font-medium">{name}</span>;
  return (
    <Link href={`/notes/${encodeURIComponent(line.note_id)}`} className="font-medium hover:underline">
      {name}
    </Link>
  );
}

function codeText(line: RemittanceLine): string {
  const billed = line.billed_code ?? FORMAT_WORDS.empty;
  const paid = line.paid_code ?? billed;
  return paid === billed ? billed : REMITTANCE_TEXT.codeChange(billed, paid);
}

function LineRow({ line, onDraft }: { line: RemittanceLine; onDraft: (lineId: string) => void }) {
  return (
    <Tr>
      <Td>
        <PatientCell line={line} />
      </Td>
      <Td className="text-secondary tabular-nums">{line.service_date ? formatCalendarDay(line.service_date) : FORMAT_WORDS.empty}</Td>
      <Td className="tabular-nums">{codeText(line)}</Td>
      <Td className="text-right text-secondary tabular-nums">
        {REMITTANCE_TEXT.amounts(formatCents(line.billed_amount), formatCents(line.paid_amount))}
      </Td>
      <Td>
        <StatusDot tone={STATUS_TONES[line.status]}>{REMITTANCE_TEXT.status[line.status]}</StatusDot>
      </Td>
      <Td className="text-secondary tabular-nums">{line.appeal_by ? formatCalendarDay(line.appeal_by, "year") : FORMAT_WORDS.empty}</Td>
      <Td className="text-right">
        {canAppeal(line) ? (
          <Button size="sm" onClick={() => onDraft(line.id)}>
            {REMITTANCE_TEXT.draftAppeal}
          </Button>
        ) : null}
      </Td>
    </Tr>
  );
}

export function RemittanceLines({ lines, onDraft }: RemittanceLinesProps) {
  const words = REMITTANCE_TEXT.lineColumns;
  return (
    <Table label={REMITTANCE_TEXT.linesLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{words.patient}</Th>
          <Th>{words.serviceDate}</Th>
          <Th>{words.codes}</Th>
          <Th className="text-right">{words.amounts}</Th>
          <Th>{words.status}</Th>
          <Th>{words.appealBy}</Th>
          <Th>
            <span className="sr-only">{REMITTANCE_TEXT.draftAppeal}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {lines.map((line) => (
          <LineRow key={line.id} line={line} onDraft={onDraft} />
        ))}
      </tbody>
    </Table>
  );
}
