"use client";

import { useCallback, useState } from "react";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import { useRemote } from "@/hooks/useRemote";
import { getEmailIntake } from "@/lib/api/emailIntake";
import type { EmailIntake as EmailIntakeData } from "@/lib/api/types";
import { AllowedSenders } from "./AllowedSenders";
import { IntakeAddress } from "./IntakeAddress";
import { IntakeMessages } from "./IntakeMessages";
import { IntakeTestCheck } from "./IntakeTestCheck";
import { EMAIL_INTAKE_TEXT } from "./strings";

export const EMAIL_INTAKE_KEY = "practice-email-intake";

const words = EMAIL_INTAKE_TEXT;
const REMOTE_TEXT = { loading: words.loading, empty: words.loading, retry: words.retry };

function statusOf(intake: EmailIntakeData): { tone: StatusTone; label: string } {
  if (!intake.available) return { tone: "neutral", label: words.unavailable };
  return intake.address ? { tone: "ok", label: words.receiving } : { tone: "neutral", label: words.off };
}

function EmailIntakeBody({ intake, onChange }: { intake: EmailIntakeData; onChange: (next: EmailIntakeData) => void }) {
  const [version, setVersion] = useState(0);
  const refreshMessages = useCallback(() => setVersion((value) => value + 1), []);
  const status = statusOf(intake);
  return (
    <>
      <div className="flex h-12 items-center justify-between gap-3 border-t border-hairline px-4">
        <span className="text-subhead font-medium text-label">{words.status}</span>
        <StatusDot tone={status.tone}>{status.label}</StatusDot>
      </div>
      {intake.available ? (
        <>
          <IntakeAddress intake={intake} onChange={onChange} />
          <AllowedSenders senders={intake.senders} onChange={onChange} />
          {intake.address ? <IntakeTestCheck onArrived={refreshMessages} /> : null}
          <IntakeMessages version={version} />
        </>
      ) : null}
    </>
  );
}

export function EmailIntake() {
  const remote = useRemote(EMAIL_INTAKE_KEY, getEmailIntake);
  return (
    <Panel aria-label={words.title}>
      <PanelHeader title={words.title} />
      <RemoteView state={remote.state} text={REMOTE_TEXT} onRetry={remote.reload}>
        {(intake) => <EmailIntakeBody intake={intake} onChange={remote.replace} />}
      </RemoteView>
    </Panel>
  );
}
