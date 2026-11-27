import { formatCounted } from "@/components/shared/rates";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import type { AgreementSide, AgreementSummary } from "@/lib/api/types";
import { FORMAT_WORDS, formatCount, formatPercent } from "@/lib/format";
import { rateRows, type Display } from "../qualityModel";
import { QUALITY_TEXT } from "../strings";
import { IntervalChart } from "./IntervalChart";
import { IntervalTable } from "./IntervalTable";

interface SampleSummaryPanelProps {
  summary: AgreementSummary;
  side: AgreementSide;
  display: Display;
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-footnote text-secondary">{label}</dt>
      <dd className="m-0 text-body font-medium tabular-nums">{value}</dd>
    </div>
  );
}

export function SampleSummaryPanel({ summary, side, display }: SampleSummaryPanelProps) {
  const sideName = QUALITY_TEXT.sides[side];
  const label = QUALITY_TEXT.summaryLabel(sideName);
  const rows = rateRows(summary);
  const words = QUALITY_TEXT.directions;
  return (
    <Panel>
      <PanelHeader title={QUALITY_TEXT.summaryTitle} actions={<span className="text-footnote text-secondary">{QUALITY_TEXT.notesCount(formatCount(summary.notes))}</span>} />
      <div className="flex flex-col gap-5 px-4 pb-5">
        {display === "chart" ? <IntervalChart rows={rows} label={label} /> : <IntervalTable rows={rows} label={label} />}
        <dl aria-label={QUALITY_TEXT.directionTitle} className="m-0 grid grid-cols-[repeat(auto-fit,minmax(9rem,1fr))] gap-4 border-t border-hairline pt-4">
          <Fact label={words.higher(sideName)} value={formatCounted(summary.em_higher)} />
          <Fact label={words.lower(sideName)} value={formatCounted(summary.em_lower)} />
          <Fact label={words.other} value={formatCount(summary.em_other)} />
          <Fact label={QUALITY_TEXT.f1} value={summary.icd_f1 === null ? FORMAT_WORDS.empty : formatPercent(summary.icd_f1)} />
        </dl>
      </div>
    </Panel>
  );
}
