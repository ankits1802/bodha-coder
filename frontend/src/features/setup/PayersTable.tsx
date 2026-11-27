import { Button } from "@/components/ui/Button";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { Payer } from "@/lib/api/types";
import { FORMAT_WORDS } from "@/lib/format";
import { PAYER_TEXT } from "./strings";

interface PayersTableProps {
  payers: Payer[];
  onEdit: (payer: Payer) => void;
  onRemove: (payer: Payer) => void;
}

export function PayersTable({ payers, onEdit, onRemove }: PayersTableProps) {
  const columns = PAYER_TEXT.columns;
  return (
    <Table label={PAYER_TEXT.tableLabel} minWidth="md">
      <thead>
        <tr>
          <Th>{columns.name}</Th>
          <Th>{columns.payerId}</Th>
          <Th>{columns.planType}</Th>
          <Th>{columns.status}</Th>
          <Th>
            <span className="sr-only">{columns.actions}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {payers.map((payer) => (
          <Tr key={payer.id}>
            <Td className="font-medium">{payer.name}</Td>
            <Td className="text-secondary tabular-nums">{payer.payer_id ?? FORMAT_WORDS.empty}</Td>
            <Td className="text-secondary">{PAYER_TEXT.planTypes[payer.plan_type]}</Td>
            <Td>
              <StatusDot tone={payer.active ? "ok" : "neutral"}>{payer.active ? PAYER_TEXT.active : PAYER_TEXT.inactive}</StatusDot>
            </Td>
            <Td className="text-right whitespace-nowrap">
              <Button variant="plain" size="sm" aria-label={PAYER_TEXT.editFor(payer.name)} onClick={() => onEdit(payer)}>
                {PAYER_TEXT.edit}
              </Button>
              <Button variant="plain" size="sm" aria-label={PAYER_TEXT.removeFor(payer.name)} onClick={() => onRemove(payer)}>
                {PAYER_TEXT.remove}
              </Button>
            </Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
