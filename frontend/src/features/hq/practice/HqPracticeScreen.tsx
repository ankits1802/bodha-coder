"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { StatusDot } from "@/components/ui/StatusDot";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getHqPracticePage } from "@/lib/api/hq";
import type { HqPractice, HqPracticePage } from "@/lib/api/types";
import { isClosed, practiceStatusView } from "../practiceStatus";
import { AppointAdminDialog } from "../practices/AppointAdminDialog";
import { EditPracticeDialog } from "../practices/EditPracticeDialog";
import { RenewDialog } from "../practices/RenewDialog";
import { HQ_TEXT } from "../strings";
import { ActivityTab } from "./ActivityTab";
import { PeopleTab } from "./PeopleTab";
import { PlacesTab } from "./PlacesTab";
import { PlanTab } from "./PlanTab";
import { PRACTICE_TABS, tabFrom, type PracticeTab } from "./practiceTabs";
import { SpendTab } from "./SpendTab";

type OpenDialog = "renew" | "edit" | "appoint" | null;

const words = HQ_TEXT.practice;
const SEGMENTS = PRACTICE_TABS.map((value) => ({ value, label: words.tabs[value] }));

function TabBody({ tab, page }: { tab: PracticeTab; page: HqPracticePage }) {
  if (tab === "plan") return <PlanTab practice={page.practice} />;
  if (tab === "spend") return <SpendTab scope={{ practice_id: page.practice.id }} />;
  if (tab === "activity") return <ActivityTab practice={page.practice} />;
  if (tab === "places") return <PlacesTab places={page.places} />;
  return <PeopleTab practiceId={page.practice.id} />;
}

function StatusLine({ practice }: { practice: HqPractice }) {
  const status = practiceStatusView(practice);
  return <StatusDot tone={status.tone}>{status.label}</StatusDot>;
}

function HeaderActions({ onOpen }: { onOpen: (dialog: OpenDialog) => void }) {
  return (
    <>
      <Button onClick={() => onOpen("appoint")}>{words.addAdmin}</Button>
      <Button onClick={() => onOpen("edit")}>{words.edit}</Button>
      <Button variant="primary" onClick={() => onOpen("renew")}>
        {words.renew}
      </Button>
    </>
  );
}

export function HqPracticeScreen({ practiceId }: { practiceId: string }) {
  const remote = useRemote(`hq-practice:${practiceId}`, () => getHqPracticePage(practiceId));
  const query = useQueryParams();
  const tab = tabFrom(query.get("tab"));
  const [dialog, setDialog] = useState<OpenDialog>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const practice = remote.state.status === "success" ? remote.state.data.practice : null;

  function open(next: OpenDialog): void {
    setNotice(null);
    setDialog(next);
  }

  function finished(message: string): void {
    setDialog(null);
    setNotice(message);
    remote.reload();
  }

  return (
    <>
      <PageHeader
        title={practice?.name ?? words.title}
        subtitle={practice ? <StatusLine practice={practice} /> : undefined}
        actions={practice && !isClosed(practice) ? <HeaderActions onOpen={open} /> : null}
      />
      {notice ? <InlineAlert tone="ok">{notice}</InlineAlert> : null}
      <SegmentedControl<PracticeTab>
        label={words.tabsLabel}
        value={tab}
        segments={SEGMENTS}
        onChange={(next) => query.update({ tab: next, offset: null, from: null, to: null })}
      />
      <RemoteView state={remote.state} text={{ loading: words.loading, empty: words.loading, retry: HQ_TEXT.retry }} onRetry={remote.reload}>
        {(data) => <TabBody tab={tab} page={data} />}
      </RemoteView>
      {practice && dialog === "renew" ? <RenewDialog subject={practice} onDone={finished} onClose={() => setDialog(null)} /> : null}
      {practice && dialog === "edit" ? (
        <EditPracticeDialog
          practice={practice}
          onClose={() => setDialog(null)}
          onSaved={() => finished(HQ_TEXT.practices.notices.saved(practice.name))}
        />
      ) : null}
      {practice && dialog === "appoint" ? (
        <AppointAdminDialog
          practice={practice}
          onClose={() => setDialog(null)}
          onAppointed={() => finished(HQ_TEXT.practices.notices.adminAppointed(practice.name))}
        />
      ) : null}
    </>
  );
}
