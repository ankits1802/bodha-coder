import { NoteLinkRow } from "@/components/shared/NoteLinkRow";
import { Panel } from "@/components/ui/Panel";
import type { QueueRow } from "@/lib/api/types";
import { COMPLIANCE_TEXT } from "../strings";

export function CaseList({ rows }: { rows: QueueRow[] }) {
  if (rows.length === 0) return null;
  return (
    <Panel aria-label={COMPLIANCE_TEXT.othersLabel}>
      <ul className="m-0 list-none divide-y divide-hairline p-0">
        {rows.map((row) => (
          <NoteLinkRow key={row.id} row={row} lane="compliance" />
        ))}
      </ul>
    </Panel>
  );
}
