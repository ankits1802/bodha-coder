"use client";

import { Button } from "@/components/ui/Button";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { StatusDot } from "@/components/ui/StatusDot";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getSampleResults } from "@/lib/api/quality";
import type { AgreementSide, SampleOverview, SampleResults } from "@/lib/api/types";
import { formatCalendarDay } from "@/lib/format";
import { DISPLAYS, SIDES, parseDisplay, parseSide, scopeName, type Display } from "../qualityModel";
import { QUALITY_TEXT } from "../strings";
import { NoteAgreementTable } from "./NoteAgreementTable";
import { ProviderAgreementTable } from "./ProviderAgreementTable";
import { SampleSummaryPanel } from "./SampleSummaryPanel";

const REMOTE_TEXT = { loading: QUALITY_TEXT.loading, empty: QUALITY_TEXT.noSamples, retry: QUALITY_TEXT.retry };
const SIDE_SEGMENTS = SIDES.map((value) => ({ value, label: QUALITY_TEXT.sides[value] }));
const DISPLAY_SEGMENTS = DISPLAYS.map((value) => ({ value, label: QUALITY_TEXT.displays[value] }));

function SampleFacts({ sample }: { sample: SampleOverview }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-body text-secondary">
      <span className="font-medium text-label">{scopeName(sample)}</span>
      <span className="tabular-nums">{QUALITY_TEXT.period(formatCalendarDay(sample.start), formatCalendarDay(sample.end))}</span>
      <span className="tabular-nums">{QUALITY_TEXT.progress(sample.done, sample.notes)}</span>
      {sample.started_by ? <span>{QUALITY_TEXT.startedBy(sample.started_by)}</span> : null}
      <StatusDot tone={sample.status === "done" ? "ok" : "neutral"}>{QUALITY_TEXT[sample.status]}</StatusDot>
    </div>
  );
}

interface ResultsBodyProps {
  results: SampleResults;
  side: AgreementSide;
  display: Display;
  onChange: (changes: Record<string, string | null>) => void;
}

function ResultsBody({ results, side, display, onChange }: ResultsBodyProps) {
  return (
    <>
      <SampleFacts sample={results.sample} />
      <div className="flex flex-wrap items-center gap-3">
        <SegmentedControl
          label={QUALITY_TEXT.sideLabel}
          value={side}
          segments={SIDE_SEGMENTS}
          onChange={(value) => onChange({ against: value === "bodha" ? null : value })}
        />
        <SegmentedControl
          label={QUALITY_TEXT.displayLabel}
          value={display}
          segments={DISPLAY_SEGMENTS}
          onChange={(value) => onChange({ display: value === "chart" ? null : value })}
        />
      </div>
      <SampleSummaryPanel summary={results.summary[side]} side={side} display={display} />
      <ProviderAgreementTable providers={results.providers} side={side} />
      <NoteAgreementTable items={results.items} side={side} />
    </>
  );
}

export function SampleResultsView({ sampleId }: { sampleId: string }) {
  const params = useQueryParams();
  const results = useRemote(`quality-sample:${sampleId}`, () => getSampleResults(sampleId));
  return (
    <>
      <div>
        <Button variant="plain" size="sm" onClick={() => params.update({ sample: null, against: null, display: null })}>
          {QUALITY_TEXT.back}
        </Button>
      </div>
      <RemoteView state={results.state} text={REMOTE_TEXT} onRetry={results.reload}>
        {(data) => (
          <ResultsBody
            results={data}
            side={parseSide(params.get("against"))}
            display={parseDisplay(params.get("display"))}
            onChange={params.update}
          />
        )}
      </RemoteView>
    </>
  );
}
