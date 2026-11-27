"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getSamples } from "@/lib/api/quality";
import { QUALITY_TEXT } from "../strings";
import { SampleTable } from "./SampleTable";
import { StartSampleDialog } from "./StartSampleDialog";

const REMOTE_TEXT = { loading: QUALITY_TEXT.loading, empty: QUALITY_TEXT.noSamples, retry: QUALITY_TEXT.retry };

export function AuditsView() {
  const params = useQueryParams();
  const samples = useRemote("quality-samples", getSamples);
  const [starting, setStarting] = useState(false);
  const open = (sampleId: string) => params.update({ sample: sampleId });

  return (
    <Panel>
      <PanelHeader
        title={QUALITY_TEXT.samplesTitle}
        actions={
          <Button variant="primary" size="sm" onClick={() => setStarting(true)}>
            {QUALITY_TEXT.startAudit}
          </Button>
        }
      />
      <RemoteView state={samples.state} text={REMOTE_TEXT} isEmpty={(data) => data.length === 0} onRetry={samples.reload}>
        {(data) => <SampleTable samples={data} onOpen={open} />}
      </RemoteView>
      {starting ? (
        <StartSampleDialog
          onClose={() => setStarting(false)}
          onStarted={(sampleId) => {
            setStarting(false);
            open(sampleId);
          }}
        />
      ) : null}
    </Panel>
  );
}
