"use client";

import { useState } from "react";
import { usePracticeSwitch } from "@/components/shared/sidebar/usePracticeSwitch";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { setCombinedBilling } from "@/lib/api/organizations";
import type { MyOrganizationPractice } from "@/lib/api/types";
import { useSession } from "@/lib/session/useSession";
import { AddPersonDialog } from "./AddPersonDialog";
import { GetAccessDialog } from "./GetAccessDialog";
import { NewPracticeDialog } from "./NewPracticeDialog";
import { PracticeTable } from "./PracticeTable";
import { ORGANIZATION_TEXT } from "./strings";
import { useOrganization } from "./useOrganizationData";

type OpenDialog = "practice" | "person" | null;

const words = ORGANIZATION_TEXT.practices;
const TEXT = { loading: ORGANIZATION_TEXT.loading, empty: words.empty, retry: ORGANIZATION_TEXT.retry };

export function OrganizationPracticesScreen({ organizationId }: { organizationId: string }) {
  const remote = useOrganization(organizationId);
  const { user } = useSession();
  const switching = usePracticeSwitch(user?.practice?.id ?? null);
  const combined = useAction(setCombinedBilling);
  const [dialog, setDialog] = useState<OpenDialog>(null);
  const [access, setAccess] = useState<MyOrganizationPractice | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const overview = remote.state.status === "success" ? remote.state.data : null;
  const openPractices = overview?.practices.filter((practice) => practice.open) ?? [];

  async function toggle(practice: MyOrganizationPractice, next: boolean): Promise<void> {
    setNotice(null);
    if ((await combined.run(organizationId, practice.id, next)).ok) remote.reload();
  }

  function added(message: string): void {
    setDialog(null);
    setNotice(message);
    remote.reload();
  }

  const actions = (
    <>
      <Button disabled={!overview} onClick={() => setDialog("person")}>
        {words.addPerson}
      </Button>
      <Button variant="primary" onClick={() => setDialog("practice")}>
        {words.newPractice}
      </Button>
    </>
  );

  return (
    <>
      <PageHeader title={overview?.name ?? words.title} actions={actions} />
      {notice ? <InlineAlert tone="ok">{notice}</InlineAlert> : null}
      {combined.error ? <InlineAlert tone="bad">{combined.error}</InlineAlert> : null}
      {switching.error ? <InlineAlert tone="bad">{switching.error}</InlineAlert> : null}
      <Panel aria-label={words.tableLabel}>
        <RemoteView state={remote.state} text={TEXT} isEmpty={(data) => data.practices.length === 0} onRetry={remote.reload}>
          {(data) => (
            <PracticeTable
              practices={data.practices}
              busy={combined.pending || switching.pending}
              onCombined={(practice, next) => void toggle(practice, next)}
              onOpen={(practice) => void switching.choose(practice.id)}
              onGetAccess={setAccess}
            />
          )}
        </RemoteView>
      </Panel>
      {dialog === "practice" ? (
        <NewPracticeDialog organizationId={organizationId} onClose={() => setDialog(null)} onAdded={(name) => added(words.added(name))} />
      ) : null}
      {dialog === "person" ? (
        <AddPersonDialog
          organizationId={organizationId}
          practices={openPractices}
          onClose={() => setDialog(null)}
          onAdded={(name) => added(words.personAdded(name))}
        />
      ) : null}
      {access ? (
        <GetAccessDialog
          organizationId={organizationId}
          practice={access}
          onClose={() => setAccess(null)}
          onGranted={remote.reload}
          onOpen={(practiceId) => void switching.choose(practiceId)}
        />
      ) : null}
    </>
  );
}
