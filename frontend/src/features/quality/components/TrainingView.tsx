"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { getTrainingSets } from "@/lib/api/quality";
import { QUALITY_TEXT } from "../strings";
import { AssignTrainingDialog } from "./AssignTrainingDialog";
import { TrainingSetsTable } from "./TrainingSetsTable";

const WORDS = QUALITY_TEXT.training;
const REMOTE_TEXT = { loading: QUALITY_TEXT.loading, empty: WORDS.empty, retry: QUALITY_TEXT.retry };

export function TrainingView() {
  const sets = useRemote("training-sets", getTrainingSets);
  const [assigning, setAssigning] = useState(false);
  return (
    <Panel>
      <PanelHeader
        title={WORDS.title}
        actions={
          <Button size="sm" variant="primary" onClick={() => setAssigning(true)}>
            {WORDS.assign}
          </Button>
        }
      />
      <RemoteView state={sets.state} text={REMOTE_TEXT} isEmpty={(data) => data.length === 0} onRetry={sets.reload}>
        {(data) => <TrainingSetsTable sets={data} />}
      </RemoteView>
      {assigning ? (
        <AssignTrainingDialog
          onClose={() => setAssigning(false)}
          onAssigned={() => {
            setAssigning(false);
            sets.reload();
          }}
        />
      ) : null}
    </Panel>
  );
}
