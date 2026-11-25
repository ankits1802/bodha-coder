"use client";

import { useState } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import type { Role, TodaySummary } from "@/lib/api/types";
import { getToday } from "@/lib/api/work";
import { formatDay } from "@/lib/format";
import { canUse } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { BeingRead } from "./components/BeingRead";
import { LaneCells } from "./components/LaneCells";
import { UpNext } from "./components/UpNext";
import { TODAY_TEXT } from "./strings";
import { usePlaceNames } from "./usePlaceNames";

const REMOTE_TEXT = { loading: TODAY_TEXT.loading, empty: TODAY_TEXT.empty, retry: TODAY_TEXT.retry };

function TodayActions({ role, firstNoteId }: { role: Role; firstNoteId: string | null }) {
  const reviewHref = firstNoteId ? `/notes/${encodeURIComponent(firstNoteId)}?lane=coder` : "/queue";
  return (
    <>
      {canUse(role, "upload") ? <ButtonLink href="/upload">{TODAY_TEXT.upload}</ButtonLink> : null}
      {canUse(role, "queue") ? (
        <ButtonLink href={reviewHref} variant="primary">
          {TODAY_TEXT.startReviewing}
        </ButtonLink>
      ) : null}
    </>
  );
}

function TodayBody({ data, role }: { data: TodaySummary; role: Role }) {
  const placeNames = usePlaceNames(canUse(role, "upload"));
  return (
    <>
      <LaneCells counts={data.lanes} role={role} />
      <div className="flex flex-wrap items-start gap-6">
        {canUse(role, "queue") ? <UpNext rows={data.next_up} /> : null}
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

function TodayContent({ role }: { role: Role }) {
  const today = useRemote("today", getToday);
  const [now] = useState(() => new Date());
  const firstNoteId = today.state.status === "success" ? (today.state.data.next_up[0]?.id ?? null) : null;
  return (
    <>
      <PageHeader
        title={TODAY_TEXT.title}
        subtitle={formatDay(now, "full")}
        actions={<TodayActions role={role} firstNoteId={firstNoteId} />}
      />
      <RemoteView state={today.state} text={REMOTE_TEXT} onRetry={today.reload}>
        {(data) => <TodayBody data={data} role={role} />}
      </RemoteView>
    </>
  );
}

export function TodayScreen() {
  const { user } = useSession();
  return <AreaGuard area="today">{user ? <TodayContent role={user.role} /> : null}</AreaGuard>;
}
