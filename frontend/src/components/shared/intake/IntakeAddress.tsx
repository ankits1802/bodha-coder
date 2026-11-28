"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { useCopy } from "@/hooks/useCopy";
import { issueIntakeAddress, retireIntakeAddress } from "@/lib/api/emailIntake";
import type { EmailIntake } from "@/lib/api/types";
import { formatInstantDay } from "@/lib/format";
import { EMAIL_INTAKE_TEXT } from "./strings";

interface IntakeAddressProps {
  intake: EmailIntake;
  onChange: (intake: EmailIntake) => void;
}

type Confirming = "replace" | "off" | null;

const words = EMAIL_INTAKE_TEXT;

function EarlierAddresses({ intake }: { intake: EmailIntake }) {
  const shown = intake.previous.filter((item) => item.address !== null);
  if (shown.length === 0) return null;
  return (
    <details className="text-subhead text-secondary">
      <summary className="cursor-pointer">{words.previous}</summary>
      <ul className="m-0 mt-2 flex list-none flex-col gap-1 p-0">
        {shown.map((item) => (
          <li key={`${item.address}-${item.since}`} className="flex flex-wrap justify-between gap-3">
            <span className="break-all">{item.address}</span>
            <span className="tabular-nums">
              {formatInstantDay(item.since)}
              {item.until ? ` – ${formatInstantDay(item.until)}` : ""}
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}

export function IntakeAddress({ intake, onChange }: IntakeAddressProps) {
  const [confirming, setConfirming] = useState<Confirming>(null);
  const copier = useCopy();
  const issue = useAction(issueIntakeAddress);
  const retire = useAction(retireIntakeAddress);
  const confirmed = confirming === "off" ? retire : issue;

  async function change(action: typeof issue): Promise<void> {
    const outcome = await action.run();
    if (!outcome.ok) return;
    setConfirming(null);
    copier.reset();
    onChange(outcome.value);
  }

  if (!intake.address) {
    return (
      <div className="flex flex-col gap-3 border-t border-hairline px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-subhead font-medium text-label">{words.address}</span>
          <Button variant="primary" pending={issue.pending} onClick={() => void change(issue)}>
            {words.getAddress}
          </Button>
        </div>
        {issue.error ? <InlineAlert tone="bad">{issue.error}</InlineAlert> : null}
        <EarlierAddresses intake={intake} />
      </div>
    );
  }
  const address = intake.address;
  return (
    <div className="flex flex-col gap-3 border-t border-hairline px-4 py-4">
      <span className="text-subhead font-medium text-label">{words.address}</span>
      <div className="flex flex-wrap items-center gap-2">
        <output aria-label={words.address} className="min-w-0 rounded-field bg-muted-panel px-3 py-2 text-callout font-medium break-all select-all">
          {address}
        </output>
        <Button size="sm" onClick={() => void copier.copy(address)}>
          {words.copy}
        </Button>
        {copier.state !== "idle" ? (
          <span role="status" className="text-subhead text-secondary">
            {copier.state === "copied" ? words.copied : words.copyFailed}
          </span>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => setConfirming("replace")}>
          {words.newAddress}
        </Button>
        <Button size="sm" variant="danger" onClick={() => setConfirming("off")}>
          {words.turnOff}
        </Button>
      </div>
      <EarlierAddresses intake={intake} />
      <ConfirmDialog
        open={confirming !== null}
        title={confirming === "off" ? words.turnOffTitle : words.newAddressTitle}
        confirmLabel={confirming === "off" ? words.turnOff : words.replace}
        cancelLabel={words.cancel}
        destructive
        pending={confirmed.pending}
        error={confirmed.error}
        onConfirm={() => void change(confirmed)}
        onClose={() => setConfirming(null)}
      />
    </div>
  );
}
