"use client";

import { useState } from "react";
import { useAction } from "@/hooks/useAction";
import { removeMember, resendInvite, resetMemberMfa, sendPasswordReset, updateMember } from "@/lib/api/team";
import type { PracticeRole, TeamMember } from "@/lib/api/types";
import { TEAM_TEXT, type ConfirmKind, type SendKind } from "./strings";

export interface PendingConfirm {
  kind: ConfirmKind;
  member: TeamMember;
}

function runConfirmed({ kind, member }: PendingConfirm): Promise<void> {
  if (kind === "reset") return resetMemberMfa(member.id);
  if (kind === "remove") return removeMember(member.id);
  return updateMember(member.id, { blocked: kind === "block" });
}

function runTask(task: () => Promise<void>): Promise<void> {
  return task();
}

export function useTeamActions(onChanged: () => void) {
  const [pending, setPending] = useState<PendingConfirm | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const quick = useAction(runTask);
  const confirmed = useAction(runConfirmed);

  async function changeRole(member: TeamMember, role: PracticeRole): Promise<void> {
    setNotice(null);
    const outcome = await quick.run(() => updateMember(member.id, { role }));
    if (!outcome.ok) return;
    setNotice(TEAM_TEXT.roleChanged(member.name));
    onChanged();
  }

  async function send(kind: SendKind, member: TeamMember): Promise<void> {
    setNotice(null);
    const outcome = await quick.run(() => (kind === "invite" ? resendInvite(member.id) : sendPasswordReset(member.id)));
    if (outcome.ok) setNotice(TEAM_TEXT.sent[kind](member.email));
  }

  function openConfirm(kind: ConfirmKind, member: TeamMember): void {
    confirmed.clearError();
    setPending({ kind, member });
  }

  async function confirmPending(): Promise<void> {
    if (!pending) return;
    const outcome = await confirmed.run(pending);
    if (!outcome.ok) return;
    setPending(null);
    onChanged();
  }

  return {
    notice,
    error: quick.error,
    pendingConfirm: pending,
    confirmBusy: confirmed.pending,
    confirmError: confirmed.error,
    changeRole,
    send,
    openConfirm,
    closeConfirm: () => setPending(null),
    confirmPending,
  };
}
