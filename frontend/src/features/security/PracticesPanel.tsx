"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { useAction } from "@/hooks/useAction";
import { NEW_PRACTICE_PATH, leavePractice } from "@/lib/api/auth";
import { refreshSession } from "@/lib/api/client";
import type { PracticeChoice, User } from "@/lib/api/types";
import { signOut } from "@/lib/session/signOut";
import { PracticeList } from "./PracticeList";
import { SECURITY_TEXT } from "./strings";

async function leave(practice: PracticeChoice, current: boolean): Promise<void> {
  await leavePractice(practice.id);
  if (current) await signOut();
  else await refreshSession();
}

export function PracticesPanel({ user }: { user: User }) {
  const words = SECURITY_TEXT.practices;
  const [leaving, setLeaving] = useState<PracticeChoice | null>(null);
  const action = useAction(leave);
  const currentId = user.practice?.id ?? null;

  function ask(practice: PracticeChoice): void {
    action.clearError();
    setLeaving(practice);
  }

  async function confirm(): Promise<void> {
    if (!leaving) return;
    const outcome = await action.run(leaving, leaving.id === currentId);
    if (outcome.ok) setLeaving(null);
  }

  const create = (
    <ButtonLink href={NEW_PRACTICE_PATH} size="sm">
      {words.newPractice}
    </ButtonLink>
  );

  return (
    <Panel aria-label={words.title} className="max-w-180">
      <PanelHeader title={words.title} actions={create} />
      <PracticeList practices={user.practices} currentId={currentId} onLeave={ask} />
      <ConfirmDialog
        open={leaving !== null}
        title={leaving ? words.confirmTitle(leaving.name) : ""}
        confirmLabel={words.leave}
        cancelLabel={words.cancel}
        destructive
        pending={action.pending}
        error={action.error}
        onConfirm={() => void confirm()}
        onClose={() => setLeaving(null)}
      />
    </Panel>
  );
}
