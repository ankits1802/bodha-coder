import { formatInterval } from "@/components/shared/rates";
import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import type { TrainingOverview, WilsonRate } from "@/lib/api/types";
import { FORMAT_WORDS, formatCount, formatPercent } from "@/lib/format";
import { TRAINING_TEXT } from "../strings";

function value(rate: WilsonRate): string {
  return rate.value === null ? FORMAT_WORDS.empty : formatPercent(rate.value);
}

function note(rate: WilsonRate): string | undefined {
  return rate.value === null ? undefined : formatInterval(rate);
}

export function ScoreStats({ scores }: { scores: TrainingOverview["scores"] }) {
  const words = TRAINING_TEXT.scores;
  const claim = scores.claim;
  return (
    <StatGrid label={TRAINING_TEXT.scoresLabel}>
      <StatCell label={words.notes} value={formatCount(claim.notes)} />
      <StatCell label={words.em} value={value(claim.em)} note={note(claim.em)} />
      <StatCell label={words.f1} value={claim.icd_f1 === null ? FORMAT_WORDS.empty : formatPercent(claim.icd_f1)} />
      <StatCell label={words.modifiers} value={value(claim.modifiers)} note={note(claim.modifiers)} />
    </StatGrid>
  );
}
