import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { PracticeInsight } from "@/lib/api/types";
import { formatCount, formatMoneyChange, formatPercent, ratio } from "@/lib/format";
import { ORGANIZATION_TEXT } from "./strings";

const words = ORGANIZATION_TEXT.insights;
const NUMBER = "text-right tabular-nums";

export function InsightTable({ practices }: { practices: readonly PracticeInsight[] }) {
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="xl">
      <thead>
        <tr>
          <Th>{columns.practice}</Th>
          <Th className="text-right">{columns.notes}</Th>
          <Th className="text-right">{columns.approved}</Th>
          <Th className="text-right">{columns.onTime}</Th>
          <Th className="text-right">{columns.matched}</Th>
          <Th className="text-right">{columns.tooLow}</Th>
          <Th className="text-right">{columns.tooHigh}</Th>
          <Th className="text-right">{columns.diagnoses}</Th>
          <Th className="text-right">{columns.difference}</Th>
        </tr>
      </thead>
      <tbody>
        {practices.map((practice) => (
          <Tr key={practice.id}>
            <Td className="text-body font-medium text-label">{practice.name}</Td>
            <Td className={NUMBER}>{formatCount(practice.notes)}</Td>
            <Td className={NUMBER}>{formatCount(practice.approved)}</Td>
            <Td className={NUMBER}>{formatPercent(ratio(practice.approved_on_time, practice.approved))}</Td>
            <Td className={NUMBER}>{formatCount(practice.outcomes.matched)}</Td>
            <Td className={NUMBER}>{formatCount(practice.outcomes.billed_too_low)}</Td>
            <Td className={NUMBER}>{formatCount(practice.outcomes.billed_too_high)}</Td>
            <Td className={NUMBER}>{formatCount(practice.outcomes.diagnosis_changes)}</Td>
            <Td className={NUMBER}>{formatMoneyChange(practice.difference)}</Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
