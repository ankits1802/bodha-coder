import { CodeChip } from "@/components/ui/CodeChip";
import { EmptyValue } from "@/components/ui/EmptyValue";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { AgreementSide, ElementComparison, SampleItemRow } from "@/lib/api/types";
import { formatCalendarDay } from "@/lib/format";
import { QUALITY_TEXT } from "../strings";

interface NoteAgreementTableProps {
  items: SampleItemRow[];
  side: AgreementSide;
}

function Verdict({ match }: { match: boolean }) {
  return <StatusDot tone={match ? "ok" : "warn"}>{match ? QUALITY_TEXT.match : QUALITY_TEXT.differs}</StatusDot>;
}

function Code({ code }: { code: string | null }) {
  return code ? <CodeChip code={code} /> : <EmptyValue />;
}

function ComparedCells({ comparison }: { comparison: ElementComparison }) {
  const { em, icd, modifiers } = comparison;
  return (
    <>
      <Td>
        <Code code={em.reference} />
      </Td>
      <Td>
        <span className="inline-flex items-center gap-2">
          <Code code={em.compared} />
          <Verdict match={em.match} />
        </span>
      </Td>
      <Td>
        <span className="inline-flex flex-wrap items-center gap-2">
          <Verdict match={icd.match} />
          {icd.match ? null : (
            <span className="text-footnote text-secondary tabular-nums">
              {QUALITY_TEXT.missingExtra(icd.missing.length, icd.extra.length)}
            </span>
          )}
        </span>
      </Td>
      <Td>
        <Verdict match={modifiers.match} />
      </Td>
    </>
  );
}

export function NoteAgreementTable({ items, side }: NoteAgreementTableProps) {
  const words = QUALITY_TEXT.noteColumns;
  return (
    <Panel>
      <PanelHeader title={QUALITY_TEXT.notesTitle} />
      <Table label={QUALITY_TEXT.notesLabel} minWidth="lg">
        <thead>
          <tr>
            <Th className="text-right">{words.position}</Th>
            <Th>{words.provider}</Th>
            <Th>{words.day}</Th>
            <Th>{words.reviewer}</Th>
            <Th>{words.auditor}</Th>
            <Th>{QUALITY_TEXT.comparedColumn(QUALITY_TEXT.sides[side])}</Th>
            <Th>{words.icd}</Th>
            <Th>{words.modifiers}</Th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <Tr key={item.id}>
              <Td className="text-right text-secondary tabular-nums">{item.position}</Td>
              <Td className="font-medium">{item.provider_name}</Td>
              <Td className="tabular-nums">{formatCalendarDay(item.service_date)}</Td>
              <Td>{item.reviewer_name}</Td>
              {item.agreement ? (
                <ComparedCells comparison={item.agreement[side]} />
              ) : (
                <Td colSpan={4}>
                  <StatusDot tone="neutral">{QUALITY_TEXT.waiting}</StatusDot>
                </Td>
              )}
            </Tr>
          ))}
        </tbody>
      </Table>
    </Panel>
  );
}
