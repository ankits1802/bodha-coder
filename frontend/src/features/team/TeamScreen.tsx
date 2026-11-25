"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getTeam } from "@/lib/api/team";
import { useSession } from "@/lib/session/useSession";
import { InviteDialog } from "./InviteDialog";
import { TEAM_TEXT } from "./strings";
import { TeamTable } from "./TeamTable";
import { ROLE_FILTERS, countIn, inFilter, isRoleFilter, seatsUsed, type RoleFilter } from "./teamModel";
import { useTeamActions } from "./useTeamActions";

export function TeamScreen() {
  const remote = useRemote("team", getTeam);
  const { user } = useSession();
  const query = useQueryParams();
  const requested = query.get("role");
  const filter: RoleFilter = isRoleFilter(requested) ? requested : "all";
  const [inviting, setInviting] = useState(false);
  const actions = useTeamActions(remote.reload);
  const team = remote.state.status === "success" ? remote.state.data : null;
  const confirm = actions.pendingConfirm;
  const words = TEAM_TEXT.confirm;

  return (
    <>
      <PageHeader
        title={TEAM_TEXT.title}
        subtitle={team ? TEAM_TEXT.seats(seatsUsed(team.members), team.seats) : undefined}
        actions={
          <Button variant="primary" onClick={() => setInviting(true)}>
            {TEAM_TEXT.invite}
          </Button>
        }
      />
      {team ? (
        <SegmentedControl<RoleFilter>
          label={TEAM_TEXT.filterLabel}
          value={filter}
          onChange={(next) => query.update({ role: next === "all" ? null : next })}
          segments={ROLE_FILTERS.map((value) => ({
            value,
            label: TEAM_TEXT.filters[value],
            count: countIn(team.members, value),
          }))}
        />
      ) : null}
      {actions.notice ? <InlineAlert tone="ok">{actions.notice}</InlineAlert> : null}
      {actions.error ? <InlineAlert tone="bad">{actions.error}</InlineAlert> : null}
      <Panel aria-label={TEAM_TEXT.tableLabel}>
        <RemoteView
          state={remote.state}
          text={{ loading: TEAM_TEXT.loading, empty: TEAM_TEXT.empty, retry: TEAM_TEXT.retry }}
          isEmpty={(data) => countIn(data.members, filter) === 0}
          onRetry={remote.reload}
        >
          {(data) => (
            <TeamTable
              members={data.members.filter((member) => inFilter(member, filter))}
              selfId={user?.id ?? null}
              onRole={(member, role) => void actions.changeRole(member, role)}
              onConfirm={actions.openConfirm}
              onSend={(kind, member) => void actions.send(kind, member)}
            />
          )}
        </RemoteView>
      </Panel>
      {inviting ? (
        <InviteDialog
          onClose={() => setInviting(false)}
          onInvited={() => {
            setInviting(false);
            remote.reload();
          }}
        />
      ) : null}
      <ConfirmDialog
        open={confirm !== null}
        title={confirm ? words.titles[confirm.kind](confirm.member.name) : ""}
        description={confirm ? words.descriptions[confirm.kind] : undefined}
        confirmLabel={confirm ? words.actions[confirm.kind] : ""}
        cancelLabel={words.cancel}
        destructive={confirm?.kind !== "unblock"}
        pending={actions.confirmBusy}
        error={actions.confirmError}
        onConfirm={() => void actions.confirmPending()}
        onClose={actions.closeConfirm}
      />
    </>
  );
}
