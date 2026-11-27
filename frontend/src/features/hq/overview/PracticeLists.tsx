import Link from "next/link";
import type { ReactNode } from "react";
import { Chevron } from "@/components/ui/Chevron";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { HqPractice } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { practiceHref } from "../practice/practiceTabs";
import { HQ_TEXT } from "../strings";
import type { AttentionItem } from "./overviewModel";

const words = HQ_TEXT.overview;

export function AttentionList({ items }: { items: AttentionItem[] }) {
  if (items.length === 0) return <EmptyState title={words.nothingNeedsAttention} />;
  return (
    <ul className="m-0 list-none p-0">
      {items.map((item, index) => (
        <li key={`${item.practice.id}:${item.reason}`} className={index === 0 ? "" : "border-t border-hairline"}>
          <Link href={practiceHref(item.practice.id)} className="flex items-center gap-3.5 px-4.5 py-3.5 hover:bg-row-hover">
            <span className="min-w-0 flex-1 font-medium">{item.practice.name}</span>
            <StatusDot tone={item.tone}>{item.reason}</StatusDot>
            <Chevron />
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function BusiestTable({ practices }: { practices: HqPractice[] }) {
  if (practices.length === 0) return <EmptyState title={words.noneWaiting} />;
  const columns = words.columns;
  return (
    <Table label={words.busiest} minWidth="sm">
      <thead>
        <tr>
          <Th>{columns.practice}</Th>
          <Th className="text-right">{columns.waiting}</Th>
          <Th className="text-right">{columns.users}</Th>
          <Th className="text-right">{columns.providers}</Th>
        </tr>
      </thead>
      <tbody>
        {practices.map((practice) => (
          <Tr key={practice.id}>
            <Td>
              <Link href={practiceHref(practice.id)} className="font-medium text-label hover:underline">
                {practice.name}
              </Link>
            </Td>
            <Td className="text-right tabular-nums">{formatCount(practice.waiting)}</Td>
            <Td className="text-right tabular-nums">{formatCount(practice.users)}</Td>
            <Td className="text-right tabular-nums">{formatCount(practice.providers)}</Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}

export function ListSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex min-w-0 flex-[1_1_20rem] flex-col gap-3">
      <h2 className="m-0 font-sans text-headline font-semibold tracking-headline">{title}</h2>
      <Panel as="div">{children}</Panel>
    </section>
  );
}
