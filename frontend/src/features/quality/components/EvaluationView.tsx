"use client";

import { formatRate } from "@/components/shared/rates";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { StatGrid, StatCell } from "@/components/ui/StatGrid";
import { StatusDot } from "@/components/ui/StatusDot";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getEvaluations, queueEvaluation } from "@/lib/api/quality";
import type { EvalRuns } from "@/lib/api/types";
import { FORMAT_WORDS, formatCount, formatPercent } from "@/lib/format";
import { changeTone } from "../qualityModel";
import { QUALITY_TEXT } from "../strings";
import { EvalCasesPanel } from "./EvalCasesPanel";
import { LevelMixPanel } from "./LevelMixPanel";
import { RunTrend } from "./RunTrend";
import { RunsTable } from "./RunsTable";

const REMOTE_TEXT = { loading: QUALITY_TEXT.loading, empty: QUALITY_TEXT.noRuns, retry: QUALITY_TEXT.retry };

function LatestStats({ data }: { data: EvalRuns }) {
  const latest = data.runs.find((run) => run.status === "done");
  const summary = latest?.summary;
  const words = QUALITY_TEXT.latest;
  return (
    <StatGrid label={words.label}>
      <StatCell label={words.cases} value={formatCount(data.cases)} />
      <StatCell label={words.em} value={summary?.em?.value != null ? formatPercent(summary.em.value) : FORMAT_WORDS.empty} note={summary?.em ? formatRate(summary.em) : undefined} />
      <StatCell label={words.f1} value={summary?.icd_f1 != null ? formatPercent(summary.icd_f1) : FORMAT_WORDS.empty} />
      <StatCell label={words.consistency} value={summary?.consistency?.all.value != null ? formatPercent(summary.consistency.all.value) : FORMAT_WORDS.empty} />
      <StatCell
        label={words.change}
        value={latest?.change ? <StatusDot tone={changeTone(latest.change)}>{QUALITY_TEXT.changes[latest.change.status]}</StatusDot> : FORMAT_WORDS.empty}
      />
    </StatGrid>
  );
}

export function EvaluationView({ canRun }: { canRun: boolean }) {
  const runs = useRemote("quality-evaluations", getEvaluations);
  const queue = useAction(queueEvaluation);
  const active = runs.state.status === "success" && runs.state.data.runs.some((run) => run.status === "queued" || run.status === "running");

  async function run(): Promise<void> {
    if ((await queue.run()).ok) runs.reload();
  }

  const actions = (
    <>
      {active ? (
        <Button size="sm" variant="plain" onClick={runs.reload}>
          {QUALITY_TEXT.refresh}
        </Button>
      ) : null}
      {canRun ? (
        <Button size="sm" variant="primary" pending={queue.pending} disabled={active} onClick={() => void run()}>
          {QUALITY_TEXT.runEvaluation}
        </Button>
      ) : null}
    </>
  );
  return (
    <>
      {runs.state.status === "success" ? <LatestStats data={runs.state.data} /> : null}
      <Panel>
        <PanelHeader title={QUALITY_TEXT.runsTitle} actions={actions} />
        {queue.error ? <InlineAlert tone="bad">{queue.error}</InlineAlert> : null}
        <RemoteView state={runs.state} text={REMOTE_TEXT} isEmpty={(data) => data.runs.length === 0} onRetry={runs.reload}>
          {(data) => (
            <>
              <RunTrend runs={data.runs} />
              <RunsTable runs={data.runs} />
            </>
          )}
        </RemoteView>
      </Panel>
      <EvalCasesPanel editable={canRun} onChanged={runs.reload} />
      <LevelMixPanel />
    </>
  );
}
