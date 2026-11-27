"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { InviteDialog } from "@/components/shared/InviteDialog";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { getHqTeam, inviteHqMember } from "@/lib/api/hq";
import type { HqTeamMember } from "@/lib/api/types";
import { useSession } from "@/lib/session/useSession";
import { HQ_TEXT } from "../strings";
import { HqTeamTable } from "./HqTeamTable";
import type { HqMemberAction } from "./hqTeamModel";
import { useHqTeamActions } from "./useHqTeamActions";

export const HQ_TEAM_KEY = "hq-team";
const words = HQ_TEXT.team;

export function HqTeamScreen() {
  const remote = useRemote(HQ_TEAM_KEY, getHqTeam);
  const { user } = useSession();
  const [inviting, setInviting] = useState(false);
  const actions = useHqTeamActions(remote.reload);
  const confirm = actions.pendingConfirm;

  function act(action: HqMemberAction, member: HqTeamMember): void {
    if (action === "resend") void actions.resendInvite(member);
    else actions.openConfirm(action, member);
  }

  return (
    <>
      <PageHeader
        title={words.title}
        actions={
          <Button variant="primary" onClick={() => setInviting(true)}>
            {words.invite}
          </Button>
        }
      />
      {actions.notice ? <InlineAlert tone="ok">{actions.notice}</InlineAlert> : null}
      {actions.error ? <InlineAlert tone="bad">{actions.error}</InlineAlert> : null}
      <Panel aria-label={words.tableLabel}>
        <RemoteView
          state={remote.state}
          text={{ loading: words.loading, empty: words.empty, retry: HQ_TEXT.retry }}
          isEmpty={(members) => members.length === 0}
          onRetry={remote.reload}
        >
          {(members) => <HqTeamTable members={members} selfId={user?.id ?? null} onAction={act} />}
        </RemoteView>
      </Panel>
      {inviting ? (
        <InviteDialog
          title={words.inviteTitle}
          formId="invite-hq-member"
          invite={inviteHqMember}
          onClose={() => setInviting(false)}
          onInvited={() => {
            setInviting(false);
            remote.reload();
          }}
        />
      ) : null}
      <ConfirmDialog
        open={confirm !== null}
        title={confirm ? words.confirm.titles[confirm.kind](confirm.member.name) : ""}
        description={confirm ? words.confirm.descriptions[confirm.kind] : undefined}
        confirmLabel={confirm ? words.confirm.actions[confirm.kind] : ""}
        cancelLabel={words.confirm.cancel}
        destructive={confirm?.kind === "deactivate"}
        pending={actions.confirmBusy}
        error={actions.confirmError}
        onConfirm={() => void actions.confirmPending()}
        onClose={actions.closeConfirm}
      />
    </>
  );
}
