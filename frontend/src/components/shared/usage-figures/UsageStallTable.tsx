import { EmptyState } from "@/components/ui/EmptyState";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { UsageStallFigures } from "@/lib/api/types";
import { formatCount, formatSeconds } from "@/lib/format";
import { ROLE_LABELS } from "@/lib/labels";
import { SpreadCell } from "./SpreadCell";
import { USAGE_TEXT } from "./strings";

const columns = USAGE_TEXT.stallColumns;

export function UsageStallTable({ rows }: { rows: UsageStallFigures[] }) {
  return (
    <Panel>
      <PanelHeader title={USAGE_TEXT.stallsTitle} />
      {rows.length === 0 ? (
        <EmptyState title={USAGE_TEXT.noStalls} />
      ) : (
        <Table label={USAGE_TEXT.stallsLabel} minWidth="md">
          <thead>
            <tr>
              <Th>{columns.task}</Th>
              <Th>{columns.step}</Th>
              <Th>{columns.role}</Th>
              <Th className="text-right">{columns.stalls}</Th>
              <Th className="text-right">{columns.people}</Th>
              <Th className="text-right">{columns.length}</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <Tr key={`${row.task}:${row.step}:${row.role}`}>
                <Td className="font-medium">{USAGE_TEXT.tasks[row.task]}</Td>
                <Td>{USAGE_TEXT.steps[row.step]}</Td>
                <Td>{ROLE_LABELS[row.role]}</Td>
                <Td className="text-right tabular-nums">{formatCount(row.stalls)}</Td>
                <Td className="text-right tabular-nums">{formatCount(row.people)}</Td>
                <SpreadCell spread={row.duration} format={formatSeconds} />
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </Panel>
  );
}
