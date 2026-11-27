"use client";

import { useState } from "react";
import { useAction } from "@/hooks/useAction";
import { resendHqInvite, updateHqMember } from "@/lib/api/hq";
import type { HqTeamMember } from "@/lib/api/types";
import { HQ_TEXT } from "../strings";
import type { HqConfirmKind } from "./hqTeamModel";

export interface PendingHqConfirm {
  kind: HqConfirmKind;
  member: HqTeamMember;
}

function runConfirmed({ kind, member }: PendingHqConfirm): Promise<void> {
  return updateHqMember(member.id, { blocked: kind === "deactivate" });
}

export function useHqTeamActions(onChanged: () => void) {
  const [pending, setPending] = useState<PendingHqConfirm | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const resend = useAction(resendHqInvite);
  const confirmed = useAction(runConfirmed);

  async function resendInvite(member: HqTeamMember): Promise<void> {
    setNotice(null);
    const outcome = await resend.run(member.id);
    if (outcome.ok) setNotice(HQ_TEXT.team.sent(member.email));
  }

  function openConfirm(kind: HqConfirmKind, member: HqTeamMember): void {
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
    error: resend.error,
    pendingConfirm: pending,
    confirmBusy: confirmed.pending,
    confirmError: confirmed.error,
    resendInvite,
    openConfirm,
    closeConfirm: () => setPending(null),
    confirmPending,
  };
}
