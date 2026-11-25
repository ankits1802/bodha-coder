"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { getMips } from "@/lib/api/practice";
import { MipsEditor } from "./MipsEditor";
import { MIPS_TEXT } from "./strings";

export function MipsSection() {
  const remote = useRemote("setup-mips", getMips);
  return (
    <Panel aria-label={MIPS_TEXT.title}>
      <PanelHeader title={MIPS_TEXT.title} />
      <RemoteView
        state={remote.state}
        text={{ loading: MIPS_TEXT.loading, empty: MIPS_TEXT.empty, retry: MIPS_TEXT.retry }}
        isEmpty={(data) => data.standard.length === 0 && data.addable.length === 0}
        onRetry={remote.reload}
      >
        {(data) => <MipsEditor key={data.measure_ids.join(",") || "standard"} overview={data} onReload={remote.reload} />}
      </RemoteView>
    </Panel>
  );
}
