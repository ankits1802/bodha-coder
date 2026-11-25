"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { useRemote } from "@/hooks/useRemote";
import { getDemoRequests } from "@/lib/api/hq";
import type { DemoRequestRow } from "@/lib/api/types";
import { FORMAT_WORDS, formatDateTime } from "@/lib/format";
import { HQ_TEXT } from "../strings";

const words = HQ_TEXT.demos;

function DemoTable({ rows }: { rows: DemoRequestRow[] }) {
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.received}</Th>
          <Th>{columns.name}</Th>
          <Th>{columns.organization}</Th>
          <Th>{columns.email}</Th>
          <Th>{columns.message}</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <Tr key={row.id}>
            <Td className="whitespace-nowrap text-secondary tabular-nums">
              <time dateTime={row.received_at}>{formatDateTime(row.received_at)}</time>
            </Td>
            <Td>{row.name}</Td>
            <Td>{row.organization}</Td>
            <Td>
              <a href={`mailto:${row.email}`} className="text-label underline underline-offset-2">
                {row.email}
              </a>
            </Td>
            <Td className="text-secondary">{row.message ?? FORMAT_WORDS.empty}</Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}

export function HqDemosScreen() {
  const demos = useRemote("hq-demo-requests", getDemoRequests);
  return (
    <>
      <PageHeader title={words.title} />
      <RemoteView
        state={demos.state}
        text={{ loading: words.loading, empty: words.empty, retry: HQ_TEXT.retry }}
        isEmpty={(rows) => rows.length === 0}
        onRetry={demos.reload}
      >
        {(rows) => <DemoTable rows={rows} />}
      </RemoteView>
    </>
  );
}
