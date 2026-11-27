"use client";

import { useState } from "react";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { useRemote } from "@/hooks/useRemote";
import { getLevelMix } from "@/lib/api/quality";
import type { LevelMix } from "@/lib/api/types";
import { FORMAT_WORDS, formatCalendarDay, formatCount, formatPercent } from "@/lib/format";
import { DISPLAYS, LEVEL_MIX_TONES, levelShares, type Display } from "../qualityModel";
import { QUALITY_TEXT } from "../strings";
import { LevelMixChart } from "./LevelMixChart";

const REMOTE_TEXT = { loading: QUALITY_TEXT.loading, empty: QUALITY_TEXT.noLevels, retry: QUALITY_TEXT.retry };
const DISPLAY_SEGMENTS = DISPLAYS.map((value) => ({ value, label: QUALITY_TEXT.displays[value] }));

function percent(share: number | null): string {
  return share === null ? FORMAT_WORDS.empty : formatPercent(share);
}

function MixTable({ mix }: { mix: LevelMix }) {
  const words = QUALITY_TEXT.mixColumns;
  return (
    <Table label={QUALITY_TEXT.mixLabel} minWidth="sm">
      <thead>
        <tr>
          <Th>{words.level}</Th>
          <Th className="text-right">{QUALITY_TEXT.mixWindows.recent}</Th>
          <Th className="text-right">{QUALITY_TEXT.mixWindows.prior}</Th>
        </tr>
      </thead>
      <tbody>
        {levelShares(mix).map((row) => (
          <Tr key={row.level}>
            <Td className="font-medium">{row.level}</Td>
            <Td className="text-right tabular-nums">{QUALITY_TEXT.mixCell(formatCount(row.recent), percent(row.recentShare))}</Td>
            <Td className="text-right tabular-nums">{QUALITY_TEXT.mixCell(formatCount(row.prior), percent(row.priorShare))}</Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}

function MixFacts({ mix }: { mix: LevelMix }) {
  const day = (iso: string) => formatCalendarDay(iso);
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1 text-footnote text-secondary tabular-nums">
      <span>{QUALITY_TEXT.mixWindow(QUALITY_TEXT.mixWindows.recent, day(mix.recent.start), day(mix.recent.end), formatCount(mix.recent.notes))}</span>
      <span>{QUALITY_TEXT.mixWindow(QUALITY_TEXT.mixWindows.prior, day(mix.prior.start), day(mix.prior.end), formatCount(mix.prior.notes))}</span>
      {mix.test ? <span>{QUALITY_TEXT.mixTest(mix.test.statistic.toFixed(2), String(mix.test.degrees_of_freedom), mix.test.p_value.toFixed(3))}</span> : null}
    </div>
  );
}

export function LevelMixPanel() {
  const mix = useRemote("quality-level-mix", getLevelMix);
  const [display, setDisplay] = useState<Display>("chart");
  const status = mix.state.status === "success" ? mix.state.data.status : null;
  const actions = (
    <>
      {status ? <StatusDot tone={LEVEL_MIX_TONES[status]}>{QUALITY_TEXT.mixStatuses[status]}</StatusDot> : null}
      <SegmentedControl label={QUALITY_TEXT.displayLabel} value={display} segments={DISPLAY_SEGMENTS} onChange={setDisplay} size="sm" />
    </>
  );
  return (
    <Panel>
      <PanelHeader title={QUALITY_TEXT.mixTitle} actions={actions} />
      <RemoteView state={mix.state} text={REMOTE_TEXT} isEmpty={(data) => data.levels.length === 0} onRetry={mix.reload}>
        {(data) => (
          <div className="flex flex-col gap-4 px-4 pb-5">
            <MixFacts mix={data} />
            {display === "chart" ? <LevelMixChart shares={levelShares(data)} /> : <MixTable mix={data} />}
          </div>
        )}
      </RemoteView>
    </Panel>
  );
}
