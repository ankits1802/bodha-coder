import { formatRate } from "@/components/shared/rates";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { EvalRunView, WilsonRate } from "@/lib/api/types";
import { FORMAT_WORDS, formatDateTime, formatPercent } from "@/lib/format";
import { RUN_TONES, changeTone } from "../qualityModel";
import { QUALITY_TEXT } from "../strings";

function rate(value: WilsonRate | undefined): string {
  return value ? formatRate(value) : FORMAT_WORDS.empty;
}

function share(value: number | null | undefined): string {
  return value === null || value === undefined ? FORMAT_WORDS.empty : formatPercent(value);
}

function ChangeCell({ run }: { run: EvalRunView }) {
  if (run.change === null) return <span className="text-quaternary">{FORMAT_WORDS.empty}</span>;
  return <StatusDot tone={changeTone(run.change)}>{QUALITY_TEXT.changes[run.change.status]}</StatusDot>;
}

export function RunsTable({ runs }: { runs: EvalRunView[] }) {
  const words = QUALITY_TEXT.runColumns;
  return (
    <Table label={QUALITY_TEXT.runsLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{words.requested}</Th>
          <Th>{words.model}</Th>
          <Th>{words.prompt}</Th>
          <Th>{words.status}</Th>
          <Th>{words.em}</Th>
          <Th className="text-right">{words.f1}</Th>
          <Th>{words.modifiers}</Th>
          <Th>{words.consistency}</Th>
          <Th>{words.change}</Th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <Tr key={run.id}>
            <Td className="tabular-nums">{run.requested_at ? formatDateTime(run.requested_at) : FORMAT_WORDS.empty}</Td>
            <Td>{run.model}</Td>
            <Td className="tabular-nums">{run.prompt_version}</Td>
            <Td>
              <StatusDot tone={RUN_TONES[run.status]}>{QUALITY_TEXT.runStatuses[run.status]}</StatusDot>
            </Td>
            <Td className="tabular-nums">{rate(run.summary.em)}</Td>
            <Td className="text-right tabular-nums">{share(run.summary.icd_f1)}</Td>
            <Td className="tabular-nums">{rate(run.summary.modifiers)}</Td>
            <Td className="tabular-nums">{rate(run.summary.consistency?.all)}</Td>
            <Td>
              <ChangeCell run={run} />
            </Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
