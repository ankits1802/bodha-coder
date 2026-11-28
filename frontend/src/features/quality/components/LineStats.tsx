import { formatInterval } from "@/components/shared/rates";
import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import type { EvalRuns } from "@/lib/api/types";
import { FORMAT_WORDS, formatPercent } from "@/lib/format";
import { type LineRate, lineRates } from "../qualityModel";
import { QUALITY_TEXT } from "../strings";

const WORDS = QUALITY_TEXT.lines;

function note({ rate, cases }: LineRate): string | undefined {
  if (cases === null) return undefined;
  if (rate === null || rate.value === null) return WORDS.cases(cases);
  return WORDS.note(formatInterval(rate), WORDS.cases(cases));
}

export function LineStats({ data }: { data: EvalRuns }) {
  const summary = data.runs.find((run) => run.status === "done")?.summary;
  return (
    <StatGrid label={WORDS.label}>
      {lineRates(summary).map((line) => (
        <StatCell
          key={line.key}
          label={WORDS[line.key]}
          value={line.rate?.value != null ? formatPercent(line.rate.value) : FORMAT_WORDS.empty}
          note={note(line)}
        />
      ))}
    </StatGrid>
  );
}
