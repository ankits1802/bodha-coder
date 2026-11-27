import { formatRate } from "@/components/shared/rates";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { SampleOverview } from "@/lib/api/types";
import { formatCalendarDay } from "@/lib/format";
import { TRAINING_TEXT } from "../strings";

export function TrainingSetsTable({ sets }: { sets: SampleOverview[] }) {
  const words = TRAINING_TEXT.setColumns;
  return (
    <Table label={TRAINING_TEXT.setsLabel} minWidth="md">
      <thead>
        <tr>
          <Th>{words.trainee}</Th>
          <Th>{words.period}</Th>
          <Th className="text-right">{words.progress}</Th>
          <Th>{words.agreement}</Th>
        </tr>
      </thead>
      <tbody>
        {sets.map((set) => (
          <Tr key={set.id}>
            <Td className="font-medium">{set.reviewers.join(", ")}</Td>
            <Td className="tabular-nums">{TRAINING_TEXT.period(formatCalendarDay(set.start), formatCalendarDay(set.end))}</Td>
            <Td className="text-right tabular-nums">{TRAINING_TEXT.progress(set.done, set.notes)}</Td>
            <Td className="tabular-nums">{formatRate(set.em_claim)}</Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
