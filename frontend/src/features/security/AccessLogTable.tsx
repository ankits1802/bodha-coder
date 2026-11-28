import Link from "next/link";
import { EmptyValue } from "@/components/ui/EmptyValue";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { AccessLogEntry } from "@/lib/api/types";
import { FORMAT_WORDS, formatDateTime } from "@/lib/format";
import { deviceOf } from "./accessLog";
import { SECURITY_TEXT } from "./strings";

export function AccessLogTable({ entries }: { entries: AccessLogEntry[] }) {
  const words = SECURITY_TEXT.log;
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.time}</Th>
          <Th>{columns.person}</Th>
          <Th>{columns.action}</Th>
          <Th>{columns.detail}</Th>
          <Th>{columns.note}</Th>
          <Th>{columns.device}</Th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry, index) => (
          <Tr key={`${entry.at}-${index}`}>
            <Td className="text-secondary tabular-nums">
              <time dateTime={entry.at}>{formatDateTime(entry.at)}</time>
            </Td>
            <Td>
              {entry.actor}
              {entry.actor_kind === "user" ? null : (
                <span className="ml-1.5 text-footnote text-tertiary">{entry.actor_kind === "provider" ? words.provider : words.system}</span>
              )}
            </Td>
            <Td>{entry.action}</Td>
            <Td className="text-secondary">{entry.detail ?? FORMAT_WORDS.empty}</Td>
            <Td>
              {entry.note_id ? (
                <Link href={`/notes/${encodeURIComponent(entry.note_id)}`} className="font-medium underline-offset-2 hover:underline">
                  {words.openNote}
                </Link>
              ) : (
                <EmptyValue />
              )}
            </Td>
            <Td className="text-secondary">{deviceOf(entry)}</Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
