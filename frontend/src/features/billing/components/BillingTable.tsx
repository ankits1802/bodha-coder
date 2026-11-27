"use client";

import Link from "next/link";
import { useState } from "react";
import { CodeList } from "@/components/shared/CodeList";
import { Panel } from "@/components/ui/Panel";
import { StatusDot } from "@/components/ui/StatusDot";
import { GroupRow, Table, Td, Th, Tr } from "@/components/ui/Table";
import type { BillingRow } from "@/lib/api/types";
import { localIsoDate } from "@/lib/dates";
import { formatCalendarDay, formatCount, formatMoney } from "@/lib/format";
import { groupByServiceDate, momentLabel } from "../billingRows";
import { BILLING_TEXT } from "../strings";

function ReviewCell({ changed }: { changed: number }) {
  if (changed > 0) return <StatusDot tone="low">{BILLING_TEXT.changed(formatCount(changed))}</StatusDot>;
  return <StatusDot tone="ok">{BILLING_TEXT.asBilled}</StatusDot>;
}

function ApprovedCell({ row, today }: { row: BillingRow; today: string }) {
  const when = row.approved_at ? momentLabel(row.approved_at, today) : null;
  return (
    <span className="flex flex-col text-secondary">
      <span>{when ? BILLING_TEXT.approvedAt(row.approved_by, when) : row.approved_by}</span>
      {row.exported_at ? (
        <span className="text-footnote text-tertiary">{BILLING_TEXT.exportedAt(momentLabel(row.exported_at, today))}</span>
      ) : null}
    </span>
  );
}

function BillingRowView({ row, today }: { row: BillingRow; today: string }) {
  return (
    <Tr>
      <Td>
        <Link href={`/notes/${encodeURIComponent(row.id)}`} className="font-medium hover:underline">
          {row.patient_name ?? row.id}
        </Link>
      </Td>
      <Td className="text-secondary">{row.provider_name}</Td>
      <Td>
        <CodeList codes={row.codes} />
      </Td>
      <Td className="text-right text-secondary tabular-nums">{formatMoney(row.estimate)}</Td>
      <Td>
        <ReviewCell changed={row.changed} />
      </Td>
      <Td>
        <ApprovedCell row={row} today={today} />
      </Td>
    </Tr>
  );
}

export function BillingTable({ rows }: { rows: BillingRow[] }) {
  const [today] = useState(() => localIsoDate());
  const words = BILLING_TEXT.columns;
  return (
    <Panel as="div">
      <Table label={BILLING_TEXT.tableLabel} minWidth="lg">
        <thead>
          <tr>
            <Th>{words.patient}</Th>
            <Th>{words.provider}</Th>
            <Th>{words.codes}</Th>
            <Th className="text-right">{words.estimate}</Th>
            <Th>{words.review}</Th>
            <Th>{words.approvedBy}</Th>
          </tr>
        </thead>
        {groupByServiceDate(rows).map((group) => (
          <tbody key={group.day}>
            <GroupRow colSpan={6}>
              {BILLING_TEXT.seenGroup(formatCalendarDay(group.day), formatCount(group.rows.length))}
            </GroupRow>
            {group.rows.map((row) => (
              <BillingRowView key={row.id} row={row} today={today} />
            ))}
          </tbody>
        ))}
      </Table>
    </Panel>
  );
}
