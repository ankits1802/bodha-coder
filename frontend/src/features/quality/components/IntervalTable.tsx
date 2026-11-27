import { formatCounted } from "@/components/shared/rates";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { FORMAT_WORDS, formatPercent } from "@/lib/format";
import type { RateRow } from "../qualityModel";
import { QUALITY_TEXT } from "../strings";

function percent(share: number | null): string {
  return share === null ? FORMAT_WORDS.empty : formatPercent(share);
}

export function IntervalTable({ rows, label }: { rows: RateRow[]; label: string }) {
  const words = QUALITY_TEXT.intervalColumns;
  return (
    <Table label={label} minWidth="sm">
      <thead>
        <tr>
          <Th>{words.element}</Th>
          <Th className="text-right">{words.agreement}</Th>
          <Th className="text-right">{words.low}</Th>
          <Th className="text-right">{words.high}</Th>
          <Th className="text-right">{words.notes}</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <Tr key={row.key}>
            <Td className="font-medium">{QUALITY_TEXT.elements[row.key]}</Td>
            <Td className="text-right tabular-nums">{percent(row.rate.value)}</Td>
            <Td className="text-right tabular-nums">{percent(row.rate.low)}</Td>
            <Td className="text-right tabular-nums">{percent(row.rate.high)}</Td>
            <Td className="text-right tabular-nums">{formatCounted(row.rate)}</Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
