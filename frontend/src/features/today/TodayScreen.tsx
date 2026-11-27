"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { prefetchNoteDetail } from "@/components/shared/noteDetail";
import { useShortcuts } from "@/components/shared/shortcuts/useShortcuts";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { usePlaceNames } from "@/hooks/usePlaceNames";
import { useRemote } from "@/hooks/useRemote";
import type { Role, TodaySummary, User } from "@/lib/api/types";
import { getToday } from "@/lib/api/work";
import { formatDay } from "@/lib/format";
import { canUse } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { FirstRunChecklist } from "./checklist/FirstRunChecklist";
import { useFirstRun } from "./checklist/useFirstRun";
import { AssignedTrainingCard } from "./components/AssignedTrainingCard";
import { BeingRead } from "./components/BeingRead";
import { LaneCells } from "./components/LaneCells";
import { TodayActions } from "./components/TodayActions";
import { UpNext } from "./components/UpNext";
import { TODAY_TEXT } from "./strings";
import { startFor } from "./todayStart";

const REMOTE_TEXT = { loading: TODAY_TEXT.loading, empty: TODAY_TEXT.empty, retry: TODAY_TEXT.retry };

function TodayBody({ data, role }: { data: TodaySummary; role: Role }) {
  const placeNames = usePlaceNames();
  return (
    <>
      <LaneCells counts={data.lanes} reasons={data.provider_reasons} role={role} />
      <div className="flex flex-wrap items-start gap-6">
        {canUse(role, "queue") ? <UpNext rows={data.next_up} placeNames={placeNames} /> : null}
        <BeingRead
          batches={data.batches}
          placeNames={placeNames}
          canUpload={canUse(role, "upload")}
          canOpenQueue={canUse(role, "queue")}
        />
      </div>
    </>
  );
}

function TodayContent({ user }: { user: User }) {
  const router = useRouter();
  const today = useRemote("today", getToday);
  const [now] = useState(() => new Date());
  const summary = today.state.status === "success" ? today.state.data : null;
  const start = summary ? startFor(user.role, summary, user.id) : null;
  const firstRun = useFirstRun(user.role === "admin");
  const checklistLeads = summary !== null && start === null;
  const noteId = start?.noteId ?? null;
  useShortcuts("today", { startReviewing: start ? () => router.push(start.href) : undefined });

  useEffect(() => {
    if (noteId) prefetchNoteDetail(noteId);
  }, [noteId]);
  return (
    <>
      <PageHeader
        title={TODAY_TEXT.title}
        subtitle={formatDay(now, "full")}
        actions={<TodayActions role={user.role} start={start} uploadLeads={checklistLeads && firstRun.status !== "loading" && !firstRun.shown} />}
      />
      <FirstRunChecklist firstRun={firstRun} lead={checklistLeads} />
      <AssignedTrainingCard enabled={canUse(user.role, "queue")} />
      <RemoteView state={today.state} text={REMOTE_TEXT} onRetry={today.reload}>
        {(data) => <TodayBody data={data} role={user.role} />}
      </RemoteView>
    </>
  );
}

export function TodayScreen() {
  const { user } = useSession();
  return <AreaGuard area="today">{user ? <TodayContent user={user} /> : null}</AreaGuard>;
}
