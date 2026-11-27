"use client";

import { useState } from "react";
import { LeavePracticeDialog } from "@/components/shared/practices/LeavePracticeDialog";
import { PRACTICE_TEXT } from "@/components/shared/practices/strings";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { NEW_PRACTICE_PATH } from "@/lib/api/auth";
import type { PracticeChoice, User } from "@/lib/api/types";
import { PracticeList } from "./PracticeList";
import { SECURITY_TEXT } from "./strings";

export function PracticesPanel({ user }: { user: User }) {
  const words = SECURITY_TEXT.practices;
  const [leaving, setLeaving] = useState<PracticeChoice | null>(null);
  const currentId = user.practice?.id ?? null;
  const create = (
    <ButtonLink href={NEW_PRACTICE_PATH} size="sm">
      {PRACTICE_TEXT.newPractice}
    </ButtonLink>
  );

  return (
    <Panel aria-label={words.title} id="practices" className="max-w-180">
      <PanelHeader title={words.title} actions={create} />
      <PracticeList practices={user.practices} currentId={currentId} onLeave={setLeaving} />
      <LeavePracticeDialog practice={leaving} currentId={currentId} onClose={() => setLeaving(null)} />
    </Panel>
  );
}
