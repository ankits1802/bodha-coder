"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { GroupRow, Table, Th } from "@/components/ui/Table";
import type { QueueRow } from "@/lib/api/types";
import { localIsoDate } from "@/lib/dates";
import { groupLabel, groupRows } from "../groupRows";
import { isSelectable, type Member } from "../queueRules";
import { QUEUE_TEXT } from "../strings";
import { QueueRowView, type RowControls } from "./QueueRowView";

interface QueueTableProps {
  rows: QueueRow[];
  selectedIds: string[];
  controls: RowControls;
  onSelectAll: (noteIds: string[]) => void;
}

function SelectAll({ rows, selectedIds, member, onSelectAll }: Omit<QueueTableProps, "controls"> & { member: Member }) {
  const eligible = rows.filter((row) => isSelectable(row, member)).map((row) => row.id);
  const allSelected = eligible.length > 0 && eligible.every((id) => selectedIds.includes(id));
  return (
    <input
      type="checkbox"
      className="size-4 accent-label"
      aria-label={QUEUE_TEXT.selectAll}
      disabled={eligible.length === 0}
      checked={allSelected}
      onChange={() => onSelectAll(allSelected ? [] : eligible)}
    />
  );
}

export function QueueTable({ rows, selectedIds, controls, onSelectAll }: QueueTableProps) {
  const [today] = useState(() => localIsoDate());
  const columns = controls.selectable ? 8 : 7;
  const words = QUEUE_TEXT.columns;
  return (
    <Panel as="div">
      <Table label={QUEUE_TEXT.tableLabel} minWidth="lg">
        <thead>
          <tr>
            {controls.selectable ? (
              <Th className="w-4">
                <SelectAll rows={rows} selectedIds={selectedIds} member={controls.member} onSelectAll={onSelectAll} />
              </Th>
            ) : null}
            <Th>{words.patient}</Th>
            <Th>{words.provider}</Th>
            <Th>{words.billed}</Th>
            <Th>{words.suggested}</Th>
            <Th>{words.status}</Th>
            <Th>{words.assigned}</Th>
            <Th className="text-right">{words.due}</Th>
          </tr>
        </thead>
        {groupRows(rows).map((group) => (
          <tbody key={group.key}>
            <GroupRow colSpan={columns}>{groupLabel(group, today)}</GroupRow>
            {group.rows.map((row) => (
              <QueueRowView key={row.id} row={row} selected={selectedIds.includes(row.id)} controls={controls} />
            ))}
          </tbody>
        ))}
      </Table>
    </Panel>
  );
}
