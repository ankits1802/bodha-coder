import { formatRate } from "@/components/shared/rates";
import { Button } from "@/components/ui/Button";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { SampleOverview } from "@/lib/api/types";
import { formatCalendarDay, formatInstantDay } from "@/lib/format";
import { scopeName } from "../qualityModel";
import { QUALITY_TEXT } from "../strings";

interface SampleTableProps {
  samples: SampleOverview[];
  onOpen: (sampleId: string) => void;
}

export function SampleTable({ samples, onOpen }: SampleTableProps) {
  const words = QUALITY_TEXT.columns;
  return (
    <Table label={QUALITY_TEXT.samplesLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{words.started}</Th>
          <Th>{words.scope}</Th>
          <Th>{words.period}</Th>
          <Th className="text-right">{words.progress}</Th>
          <Th>{words.agreement}</Th>
          <Th>{words.status}</Th>
          <Th>
            <span className="sr-only">{words.results}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {samples.map((sample) => (
          <Tr key={sample.id}>
            <Td className="tabular-nums">{formatInstantDay(sample.started_at)}</Td>
            <Td className="font-medium">{scopeName(sample)}</Td>
            <Td className="tabular-nums">{QUALITY_TEXT.period(formatCalendarDay(sample.start), formatCalendarDay(sample.end))}</Td>
            <Td className="text-right tabular-nums">{QUALITY_TEXT.progress(sample.done, sample.notes)}</Td>
            <Td className="tabular-nums">{formatRate(sample.em)}</Td>
            <Td>
              <StatusDot tone={sample.status === "done" ? "ok" : "neutral"}>{QUALITY_TEXT[sample.status]}</StatusDot>
            </Td>
            <Td className="text-right">
              <Button size="sm" variant="plain" onClick={() => onOpen(sample.id)} aria-label={QUALITY_TEXT.openResults(scopeName(sample))}>
                {QUALITY_TEXT.view}
              </Button>
            </Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
