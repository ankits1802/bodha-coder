import Link from "next/link";
import { MenuButton } from "@/components/ui/MenuButton";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { Toggle } from "@/components/ui/Toggle";
import type { OrganizationPracticeRow } from "@/lib/api/types";
import { formatCalendarDay, formatCount } from "@/lib/format";
import { PLAN_LABELS, PRACTICE_STATUS_LABELS } from "@/lib/labels";
import { practiceHref } from "../practice/practiceTabs";
import { PRACTICE_STATUS_TONES } from "../practiceStatus";
import { HQ_TEXT } from "../strings";

const words = HQ_TEXT.organization.practices;

interface OrganizationPracticesTableProps {
  practices: OrganizationPracticeRow[];
  editable: boolean;
  busy: boolean;
  onCombined: (practice: OrganizationPracticeRow, combined: boolean) => void;
  onRemove: (practice: OrganizationPracticeRow) => void;
}

type RowProps = Omit<OrganizationPracticesTableProps, "practices"> & { practice: OrganizationPracticeRow };

function PracticeRow({ practice, editable, busy, onCombined, onRemove }: RowProps) {
  const changeable = editable && practice.open;
  return (
    <Tr>
      <Td>
        <Link href={practiceHref(practice.id)} className="font-medium text-label hover:underline">
          {practice.name}
        </Link>
      </Td>
      <Td>
        {PLAN_LABELS[practice.plan]}
        {practice.renews_on ? (
          <span className="block text-footnote text-secondary">{HQ_TEXT.status.renews(formatCalendarDay(practice.renews_on, "year"))}</span>
        ) : null}
      </Td>
      <Td className="text-right tabular-nums">{formatCount(practice.users)}</Td>
      <Td className="text-right tabular-nums">{formatCount(practice.providers)}</Td>
      <Td>
        <Toggle
          label={words.combinedFor(practice.name)}
          checked={practice.combined_billing}
          disabled={!changeable || busy}
          onChange={(combined) => onCombined(practice, combined)}
        />
      </Td>
      <Td>
        <StatusDot tone={PRACTICE_STATUS_TONES[practice.status]}>{PRACTICE_STATUS_LABELS[practice.status]}</StatusDot>
      </Td>
      <Td className="w-10">
        {editable ? (
          <MenuButton
            label={HQ_TEXT.organization.moreFor(practice.name)}
            items={[{ key: "remove", label: words.remove, tone: "danger", onSelect: () => onRemove(practice) }]}
          />
        ) : null}
      </Td>
    </Tr>
  );
}

export function OrganizationPracticesTable({ practices, ...actions }: OrganizationPracticesTableProps) {
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.practice}</Th>
          <Th>{columns.plan}</Th>
          <Th className="text-right">{columns.users}</Th>
          <Th className="text-right">{columns.providers}</Th>
          <Th>{columns.combined}</Th>
          <Th>{columns.status}</Th>
          <Th className="w-10">
            <span className="sr-only">{HQ_TEXT.practices.columns.more}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {practices.map((practice) => (
          <PracticeRow key={practice.id} practice={practice} {...actions} />
        ))}
      </tbody>
    </Table>
  );
}
