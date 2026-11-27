"use client";

import Link from "next/link";
import { AssignedTable } from "@/components/shared/training/AssignedTable";
import { ASSIGNED_TEXT } from "@/components/shared/training/strings";
import { useTraining } from "@/components/shared/training/useTraining";
import { ErrorState } from "@/components/ui/ErrorState";
import { Panel } from "@/components/ui/Panel";
import { TODAY_TEXT } from "../strings";

const HEADING_ID = "today-training";

export function AssignedTrainingCard({ enabled }: { enabled: boolean }) {
  const training = useTraining(enabled);
  if (training.state.status === "loading") return null;
  if (training.state.status === "error") {
    return (
      <Panel aria-label={ASSIGNED_TEXT.title}>
        <ErrorState message={training.state.error} retryLabel={TODAY_TEXT.retry} onRetry={training.reload} />
      </Panel>
    );
  }
  const open = training.state.data.sets.filter((sample) => sample.done < sample.total);
  if (open.length === 0) return null;
  return (
    <section aria-labelledby={HEADING_ID} className="flex min-w-0 flex-col gap-3">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id={HEADING_ID} className="m-0 text-title3 font-semibold tracking-headline">
          {ASSIGNED_TEXT.title}
        </h2>
        <Link href="/training" className="text-body text-secondary hover:underline">
          {TODAY_TEXT.training.seeAll}
        </Link>
      </div>
      <Panel as="div">
        <AssignedTable samples={open} />
      </Panel>
    </section>
  );
}
