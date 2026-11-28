import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { TextButton } from "@/components/ui/TextButton";
import type { Charge } from "@/lib/api/types";
import { formatMoney } from "@/lib/format";
import { CHARGE_TEXT } from "./strings";

interface ChargesTableProps {
  charges: Charge[];
  onEdit: (charge: Charge) => void;
  onRemove: (charge: Charge) => void;
}

export function ChargesTable({ charges, onEdit, onRemove }: ChargesTableProps) {
  const words = CHARGE_TEXT.columns;
  return (
    <Table label={CHARGE_TEXT.tableLabel} minWidth="sm">
      <thead>
        <tr>
          <Th>{words.code}</Th>
          <Th className="text-right">{words.charge}</Th>
          <Th className="text-right">{words.actions}</Th>
        </tr>
      </thead>
      <tbody>
        {charges.map((charge) => (
          <Tr key={charge.code}>
            <Td className="font-medium tabular-nums">{charge.code}</Td>
            <Td className="text-right tabular-nums">{formatMoney(charge.cents / 100)}</Td>
            <Td className="text-right">
              <span className="inline-flex gap-3">
                <TextButton aria-label={CHARGE_TEXT.editFor(charge.code)} onClick={() => onEdit(charge)}>
                  {CHARGE_TEXT.edit}
                </TextButton>
                <TextButton aria-label={CHARGE_TEXT.removeFor(charge.code)} onClick={() => onRemove(charge)}>
                  {CHARGE_TEXT.remove}
                </TextButton>
              </span>
            </Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
