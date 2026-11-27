"use client";

import { useId, useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { checkDomainRecord, emailDomainAdmin, type DomainScope } from "@/lib/api/domains";
import type { AdminMailbox, DomainClaim } from "@/lib/api/types";
import { MAILBOX_OPTIONS } from "./domainModel";
import { DOMAIN_TEXT } from "./strings";

interface VerifyControlsProps {
  scope: DomainScope;
  claim: DomainClaim;
  onChanged: () => void;
}

const words = DOMAIN_TEXT;

export function VerifyControls({ scope, claim, onChanged }: VerifyControlsProps) {
  const recordId = useId();
  const [mailbox, setMailbox] = useState<AdminMailbox>("admin");
  const check = useAction(checkDomainRecord);
  const email = useAction(emailDomainAdmin);

  async function runCheck(): Promise<void> {
    email.clearError();
    if ((await check.run(scope, claim.id)).ok) onChanged();
  }

  async function sendEmail(): Promise<void> {
    check.clearError();
    if ((await email.run(scope, claim.id, mailbox)).ok) onChanged();
  }

  const error = check.error ?? email.error;
  return (
    <div className="flex flex-col gap-3">
      {claim.txt_record ? (
        <div className="flex flex-wrap items-center gap-3">
          <span id={recordId} className="text-subhead font-medium text-label">
            {words.txtRecord}
          </span>
          <code aria-labelledby={recordId} className="rounded-nav bg-control px-2 py-1 font-mono text-footnote break-all text-label select-all">
            {claim.txt_record}
          </code>
          <Button size="sm" pending={check.pending} onClick={() => void runCheck()}>
            {words.check}
          </Button>
        </div>
      ) : null}
      <div className="flex flex-wrap items-center gap-3">
        <Select
          variant="filter"
          label={words.mailboxFor(claim.domain)}
          value={mailbox}
          options={MAILBOX_OPTIONS}
          onChange={setMailbox}
        />
        <Button size="sm" pending={email.pending} onClick={() => void sendEmail()}>
          {words.sendEmail}
        </Button>
        {claim.email_sent_to ? <span className="text-subhead text-secondary">{words.emailSent(claim.email_sent_to)}</span> : null}
      </div>
      {error ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
    </div>
  );
}
