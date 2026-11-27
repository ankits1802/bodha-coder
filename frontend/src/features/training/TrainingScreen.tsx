"use client";

import { useState } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { getTraining, getTrainingSets } from "@/lib/api/quality";
import { useSession } from "@/lib/session/useSession";
import { AssignedTable } from "./components/AssignedTable";
import { AssignTrainingDialog } from "./components/AssignTrainingDialog";
import { ScoreStats } from "./components/ScoreStats";
import { TrainingSetsTable } from "./components/TrainingSetsTable";
import { TRAINING_TEXT } from "./strings";

const ASSIGNED_TEXT = { loading: TRAINING_TEXT.loading, empty: TRAINING_TEXT.noAssigned, retry: TRAINING_TEXT.retry };
const SETS_TEXT = { loading: TRAINING_TEXT.loading, empty: TRAINING_TEXT.noSets, retry: TRAINING_TEXT.retry };

function TrainingAdmin() {
  const sets = useRemote("training-sets", getTrainingSets);
  const [assigning, setAssigning] = useState(false);
  return (
    <Panel>
      <PanelHeader
        title={TRAINING_TEXT.setsTitle}
        actions={
          <Button size="sm" variant="primary" onClick={() => setAssigning(true)}>
            {TRAINING_TEXT.assign}
          </Button>
        }
      />
      <RemoteView state={sets.state} text={SETS_TEXT} isEmpty={(data) => data.length === 0} onRetry={sets.reload}>
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

function TrainingContent({ admin }: { admin: boolean }) {
  const training = useRemote("training", getTraining);
  return (
    <>
      <PageHeader title={TRAINING_TEXT.title} />
      {training.state.status === "success" && training.state.data.scores.claim.notes > 0 ? (
        <ScoreStats scores={training.state.data.scores} />
      ) : null}
      <Panel>
        <PanelHeader title={TRAINING_TEXT.assignedTitle} />
        <RemoteView state={training.state} text={ASSIGNED_TEXT} isEmpty={(data) => data.sets.length === 0} onRetry={training.reload}>
          {(data) => <AssignedTable samples={data.sets} />}
        </RemoteView>
      </Panel>
      {admin ? <TrainingAdmin /> : null}
    </>
  );
}

export function TrainingScreen() {
  const { user } = useSession();
  return <AreaGuard area="queue">{user ? <TrainingContent admin={user.role === "admin"} /> : null}</AreaGuard>;
}
