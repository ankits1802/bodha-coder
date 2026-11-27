import { Button } from "@/components/ui/Button";
import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { Toggle } from "@/components/ui/Toggle";
import type { MyOrganizationPractice, PracticeStatus } from "@/lib/api/types";
import { formatCalendarDay, formatCount } from "@/lib/format";
import { PLAN_LABELS, PRACTICE_STATUS_LABELS } from "@/lib/labels";
import { ORGANIZATION_TEXT } from "./strings";

interface PracticeTableProps {
  practices: readonly MyOrganizationPractice[];
  busy: boolean;
  onCombined: (practice: MyOrganizationPractice, combined: boolean) => void;
  onOpen: (practice: MyOrganizationPractice) => void;
  onGetAccess: (practice: MyOrganizationPractice) => void;
}

const words = ORGANIZATION_TEXT.practices;
const STATUS_TONES: Record<PracticeStatus, StatusTone> = {
  trial: "low",
  active: "ok",
  ended: "bad",
  blocked: "bad",
  closed: "neutral",
  purged: "neutral",
};

function PracticeAction({ practice, busy, onOpen, onGetAccess }: Omit<PracticeTableProps, "practices" | "onCombined"> & { practice: MyOrganizationPractice }) {
  if (!practice.open) return null;
  if (practice.my_role) {
    return (
      <Button size="sm" disabled={busy} aria-label={words.openFor(practice.name)} onClick={() => onOpen(practice)}>
        {words.open}
      </Button>
    );
  }
  return (
    <Button size="sm" disabled={busy} aria-label={words.getAccessFor(practice.name)} onClick={() => onGetAccess(practice)}>
      {words.getAccess}
    </Button>
  );
}

export function PracticeTable({ practices, busy, onCombined, onOpen, onGetAccess }: PracticeTableProps) {
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.practice}</Th>
          <Th>{columns.plan}</Th>
          <Th>{columns.combined}</Th>
          <Th className="text-right">{columns.users}</Th>
          <Th className="text-right">{columns.providers}</Th>
          <Th>
            <span className="sr-only">{columns.open}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {practices.map((practice) => (
          <Tr key={practice.id}>
            <Td>
              <div className="flex flex-col gap-1">
                <span className="text-body font-medium text-label">{practice.name}</span>
                <StatusDot tone={STATUS_TONES[practice.status]}>{PRACTICE_STATUS_LABELS[practice.status]}</StatusDot>
              </div>
            </Td>
            <Td>
              <div className="flex flex-col">
                <span className="text-body text-label">{PLAN_LABELS[practice.plan]}</span>
                {practice.renews_on ? (
                  <span className="text-subhead text-secondary">{words.renews(formatCalendarDay(practice.renews_on, "year"))}</span>
                ) : null}
              </div>
            </Td>
            <Td>
              <Toggle
                label={words.combinedFor(practice.name)}
                checked={practice.combined_billing}
                disabled={busy || !practice.open}
                onChange={(next) => onCombined(practice, next)}
              />
            </Td>
            <Td className="text-right tabular-nums">{formatCount(practice.users)}</Td>
            <Td className="text-right tabular-nums">{formatCount(practice.providers)}</Td>
            <Td className="text-right">
              <PracticeAction practice={practice} busy={busy} onOpen={onOpen} onGetAccess={onGetAccess} />
            </Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
