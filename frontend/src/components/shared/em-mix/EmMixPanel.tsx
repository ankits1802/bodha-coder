"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { getEmMix } from "@/lib/api/defensibility";
import type { InsightDays } from "@/lib/api/types";
import { EmMixView } from "./EmMixView";
import { EM_MIX_TEXT } from "./strings";

const REMOTE_TEXT = { loading: EM_MIX_TEXT.loading, empty: EM_MIX_TEXT.empty, retry: EM_MIX_TEXT.retry };

export function EmMixPanel({ days }: { days: InsightDays }) {
  const mix = useRemote(`em-mix:${days}`, () => getEmMix(days));
  return (
    <Panel aria-label={EM_MIX_TEXT.title}>
      <PanelHeader title={EM_MIX_TEXT.title} />
      <RemoteView state={mix.state} text={REMOTE_TEXT} isEmpty={(data) => data.providers.length === 0} onRetry={mix.reload}>
        {(data) => <EmMixView mix={data} />}
      </RemoteView>
    </Panel>
  );
}
