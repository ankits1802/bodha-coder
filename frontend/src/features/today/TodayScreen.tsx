"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { prefetchNoteDetail } from "@/components/shared/noteDetail";
import { useShortcuts } from "@/components/shared/shortcuts/useShortcuts";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { usePlaceNames } from "@/hooks/usePlaceNames";
import { useRemote } from "@/hooks/useRemote";
import type { Role, TodaySummary } from "@/lib/api/types";
import { getToday } from "@/lib/api/work";
import { formatDay } from "@/lib/format";
import { canUse } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { BeingRead } from "./components/BeingRead";
import { LaneCells } from "./components/LaneCells";
import { UpNext } from "./components/UpNext";
import { reviewStart } from "./reviewStart";
import { TODAY_TEXT } from "./strings";

const REMOTE_TEXT = { loading: TODAY_TEXT.loading, empty: TODAY_TEXT.empty, retry: TODAY_TEXT.retry };

function TodayActions({ role, reviewHref }: { role: Role; reviewHref: string | null }) {
  return (
    <>
      {canUse(role, "upload") ? <ButtonLink href="/upload">{TODAY_TEXT.upload}</ButtonLink> : null}
      {reviewHref && canUse(role, "queue") ? (
        <ButtonLink href={reviewHref} variant="primary">
          {TODAY_TEXT.startReviewing}
        </ButtonLink>
      ) : null}
    </>
  );
}

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

function TodayContent({ role }: { role: Role }) {
  const router = useRouter();
  const today = useRemote("today", getToday);
  const [now] = useState(() => new Date());
  const summary = today.state.status === "success" ? today.state.data : null;
  const reviewHref = summary ? reviewStart(summary) : null;
  const first = summary?.next_up[0]?.id;
  useShortcuts("today", { startReviewing: reviewHref ? () => router.push(reviewHref) : undefined });

  useEffect(() => {
    if (first && canUse(role, "queue")) prefetchNoteDetail(first);
  }, [first, role]);
  return (
    <>
      <PageHeader title={TODAY_TEXT.title} subtitle={formatDay(now, "full")} actions={<TodayActions role={role} reviewHref={reviewHref} />} />
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
