"use client";

import { AreaGuard } from "@/components/shared/AreaGuard";
import { AssignedTable } from "@/components/shared/training/AssignedTable";
import { ASSIGNED_TEXT } from "@/components/shared/training/strings";
import { useTraining } from "@/components/shared/training/useTraining";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { ScoreStats } from "./components/ScoreStats";
import { TRAINING_TEXT } from "./strings";

const ASSIGNED_REMOTE = { loading: TRAINING_TEXT.loading, empty: ASSIGNED_TEXT.empty, retry: TRAINING_TEXT.retry };

function TrainingContent() {
  const training = useTraining();
  return (
    <>
      <PageHeader title={TRAINING_TEXT.title} />
      {training.state.status === "success" && training.state.data.scores.claim.notes > 0 ? (
        <ScoreStats scores={training.state.data.scores} />
      ) : null}
      <Panel>
        <PanelHeader title={ASSIGNED_TEXT.title} />
        <RemoteView state={training.state} text={ASSIGNED_REMOTE} isEmpty={(data) => data.sets.length === 0} onRetry={training.reload}>
          {(data) => <AssignedTable samples={data.sets} />}
        </RemoteView>
      </Panel>
    </>
  );
}

export function TrainingScreen() {
  return (
    <AreaGuard area="queue">
      <TrainingContent />
    </AreaGuard>
  );
}
