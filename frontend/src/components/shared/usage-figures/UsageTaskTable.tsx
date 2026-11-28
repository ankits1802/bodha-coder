import { EmptyState } from "@/components/ui/EmptyState";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { UsageTaskFigures } from "@/lib/api/types";
import { formatCount, formatPercent, formatSeconds } from "@/lib/format";
import { ROLE_LABELS } from "@/lib/labels";
import { SpreadCell } from "./SpreadCell";
import { USAGE_TEXT } from "./strings";

const columns = USAGE_TEXT.taskColumns;

function TaskRow({ row }: { row: UsageTaskFigures }) {
  return (
    <Tr>
      <Td className="font-medium">{USAGE_TEXT.tasks[row.task]}</Td>
      <Td>{ROLE_LABELS[row.role]}</Td>
      <Td className="text-right tabular-nums">{USAGE_TEXT.finished(formatCount(row.completed), formatCount(row.tasks))}</Td>
      <Td className="text-right tabular-nums">{formatCount(row.people)}</Td>
      <SpreadCell spread={row.duration} format={formatSeconds} />
      <SpreadCell spread={row.first_decision} format={formatSeconds} />
      <SpreadCell spread={row.inputs_per_decision} format={formatCount} />
      <Td className="text-right tabular-nums">{formatPercent(row.keyboard_share)}</Td>
    </Tr>
  );
}

export function UsageTaskTable({ rows }: { rows: UsageTaskFigures[] }) {
  return (
    <Panel>
      <PanelHeader title={USAGE_TEXT.tasksTitle} />
      {rows.length === 0 ? (
        <EmptyState title={USAGE_TEXT.noTasks} />
      ) : (
        <Table label={USAGE_TEXT.tasksLabel} minWidth="lg">
          <thead>
            <tr>
              <Th>{columns.task}</Th>
              <Th>{columns.role}</Th>
              <Th className="text-right">{columns.done}</Th>
              <Th className="text-right">{columns.people}</Th>
              <Th className="text-right">{columns.time}</Th>
              <Th className="text-right">{columns.firstDecision}</Th>
              <Th className="text-right">{columns.inputs}</Th>
              <Th className="text-right">{columns.keyboard}</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <TaskRow key={`${row.task}:${row.role}`} row={row} />
            ))}
          </tbody>
        </Table>
      )}
    </Panel>
  );
}
