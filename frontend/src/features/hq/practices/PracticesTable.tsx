import Link from "next/link";
import { MenuButton, type MenuItem } from "@/components/ui/MenuButton";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { HqPractice } from "@/lib/api/types";
import { FORMAT_WORDS, formatCalendarDay, formatCount } from "@/lib/format";
import { MEMBER_STATUS_LABELS, PLAN_LABELS } from "@/lib/labels";
import { practiceStatusView, renewalLine } from "../practiceStatus";
import { practiceHref } from "../practice/practiceTabs";
import { HQ_TEXT } from "../strings";
import { adminLinkLabel, canDeletePractice, canSendAdminLink, type PracticeActionKind } from "./practiceActions";
import { billingView } from "./practiceBilling";

interface PracticesTableProps {
  practices: HqPractice[];
  onEdit: (practice: HqPractice) => void;
  onAction: (kind: PracticeActionKind, practice: HqPractice) => void;
  onAppoint: (practice: HqPractice) => void;
}

type RowActions = Omit<PracticesTableProps, "practices">;

const words = HQ_TEXT.practices;

function menuFor(practice: HqPractice, { onEdit, onAction, onAppoint }: RowActions): MenuItem[] {
  const blocked = practice.status === "blocked";
  const items: MenuItem[] = [
    { key: "edit", label: words.menu.edit, onSelect: () => onEdit(practice) },
    {
      key: "adminLink",
      label: adminLinkLabel(practice),
      disabled: !canSendAdminLink(practice),
      onSelect: () => onAction("adminLink", practice),
    },
    { key: "appointAdmin", label: words.menu.appointAdmin, onSelect: () => onAppoint(practice) },
    { key: "renew", label: words.menu.renew, onSelect: () => onAction("renew", practice) },
    blocked
      ? { key: "unblock", label: words.menu.unblock, onSelect: () => onAction("unblock", practice) }
      : { key: "block", label: words.menu.block, tone: "danger", onSelect: () => onAction("block", practice) },
  ];
  if (canDeletePractice(practice)) {
    items.push({ key: "delete", label: words.menu.delete, tone: "danger", onSelect: () => onAction("delete", practice) });
  }
  return items;
}

function AdminCell({ practice }: { practice: HqPractice }) {
  if (!practice.admin_name) return <span className="text-tertiary">{words.noAdmin}</span>;
  return (
    <span className="flex flex-col">
      <span>{practice.admin_name}</span>
      <span className="text-footnote text-secondary">{practice.admin_email ?? FORMAT_WORDS.empty}</span>
      {practice.admin_status === "invited" ? (
        <StatusDot tone="warn" className="text-footnote">
          {MEMBER_STATUS_LABELS.invited}
        </StatusDot>
      ) : null}
    </span>
  );
}

function SelfSignUp({ practice }: { practice: HqPractice }) {
  if (practice.source !== "self") return null;
  return (
    <span className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-footnote text-secondary">
      <StatusDot tone="low" className="text-footnote">
        {words.selfSignUp}
      </StatusDot>
      <span>{formatCalendarDay(practice.signed_up_on, "year")}</span>
    </span>
  );
}

function BillingLine({ practice }: { practice: HqPractice }) {
  const view = billingView(practice);
  if (!view) return null;
  return (
    <StatusDot tone={view.tone} className="mt-0.5 text-footnote">
      {view.label}
    </StatusDot>
  );
}

function PracticeRow({ practice, ...actions }: { practice: HqPractice } & RowActions) {
  const status = practiceStatusView(practice);
  return (
    <Tr>
      <Td>
        <Link href={practiceHref(practice.id)} className="font-medium text-label hover:underline">
          {practice.name}
        </Link>
        <span className="block text-footnote text-secondary">{words.providers(practice.providers)}</span>
        <SelfSignUp practice={practice} />
      </Td>
      <Td>
        <AdminCell practice={practice} />
      </Td>
      <Td className="tabular-nums">{`${formatCount(practice.users)} / ${formatCount(practice.seats)}`}</Td>
      <Td>
        {PLAN_LABELS[practice.plan]}
        <span className="block text-footnote text-secondary">{renewalLine(practice)}</span>
        <BillingLine practice={practice} />
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

export function PracticesTable({ practices, ...actions }: PracticesTableProps) {
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.practice}</Th>
          <Th>{columns.admin}</Th>
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
          <PracticeRow key={practice.id} practice={practice} {...actions} />
        ))}
      </tbody>
    </Table>
  );
}
