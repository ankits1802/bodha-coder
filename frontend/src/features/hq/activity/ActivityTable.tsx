import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { HqActivityEntry } from "@/lib/api/types";
import { FORMAT_WORDS, formatDateTime } from "@/lib/format";
import { HQ_TEXT } from "../strings";
import { actionLabel, actionTone, changeLines, practiceLabel } from "./activityModel";

interface ActivityTableProps {
  entries: HqActivityEntry[];
  names: Map<string, string>;
}

export function ActivityTable({ entries, names }: ActivityTableProps) {
  const words = HQ_TEXT.activity;
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.when}</Th>
          <Th>{columns.action}</Th>
          <Th>{columns.practice}</Th>
          <Th>{columns.detail}</Th>
          <Th>{columns.by}</Th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry, index) => (
          <Tr key={`${entry.at}-${index}`}>
            <Td className="whitespace-nowrap text-secondary tabular-nums">
              <time dateTime={entry.at}>{formatDateTime(entry.at)}</time>
            </Td>
            <Td>
              <StatusDot tone={actionTone(entry.action)}>{actionLabel(entry.action)}</StatusDot>
            </Td>
            <Td>{practiceLabel(entry.practice_id, names)}</Td>
            <Td className="text-secondary">
              {entry.detail ?? FORMAT_WORDS.empty}
              {changeLines(entry.changes).map((line) => (
                <span key={line} className="block text-footnote">
                  {line}
                </span>
              ))}
            </Td>
            <Td className="text-secondary">{entry.actor}</Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
