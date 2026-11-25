import { MenuButton, type MenuItem } from "@/components/ui/MenuButton";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { HqPractice } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { PLAN_LABELS } from "@/lib/labels";
import { practiceStatusView, renewalLine } from "../practiceStatus";
import { HQ_TEXT } from "../strings";

interface PracticesTableProps {
  practices: HqPractice[];
  onEdit: (practice: HqPractice) => void;
  onBlock: (practice: HqPractice, block: boolean) => void;
}

const words = HQ_TEXT.practices;

function menuFor(practice: HqPractice, props: Omit<PracticesTableProps, "practices">): MenuItem[] {
  const blocked = practice.status === "blocked";
  return [
    { key: "edit", label: words.menu.edit, onSelect: () => props.onEdit(practice) },
    blocked
      ? { key: "unblock", label: words.menu.unblock, onSelect: () => props.onBlock(practice, false) }
      : { key: "block", label: words.menu.block, tone: "danger", onSelect: () => props.onBlock(practice, true) },
  ];
}

function PracticeRow({ practice, ...actions }: { practice: HqPractice } & Omit<PracticesTableProps, "practices">) {
  const status = practiceStatusView(practice);
  return (
    <Tr>
      <Td>
        <span className="font-medium">{practice.name}</span>
        <span className="block text-footnote text-secondary">{words.providers(practice.providers)}</span>
      </Td>
      <Td className="tabular-nums">{`${formatCount(practice.users)} / ${formatCount(practice.seats)}`}</Td>
      <Td>
        {PLAN_LABELS[practice.plan]}
        <span className="block text-footnote text-secondary">{renewalLine(practice)}</span>
      </Td>
      <Td className="text-right tabular-nums">{formatCount(practice.waiting)}</Td>
      <Td>
        <StatusDot tone={status.tone}>{status.label}</StatusDot>
      </Td>
      <Td className="w-10">
        <MenuButton label={words.moreFor(practice.name)} items={menuFor(practice, actions)} />
      </Td>
    </Tr>
  );
}

export function PracticesTable({ practices, onEdit, onBlock }: PracticesTableProps) {
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.practice}</Th>
          <Th>{columns.users}</Th>
          <Th>{columns.plan}</Th>
          <Th className="text-right">{columns.waiting}</Th>
          <Th>{columns.status}</Th>
          <Th className="w-10">
            <span className="sr-only">{columns.more}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {practices.map((practice) => (
          <PracticeRow key={practice.id} practice={practice} onEdit={onEdit} onBlock={onBlock} />
        ))}
      </tbody>
    </Table>
  );
}
