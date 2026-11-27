"use client";

import { useState } from "react";
import { CheckToggles } from "@/components/shared/practice-checks/CheckToggles";
import { withAllChecks } from "@/components/shared/practice-checks/checkList";
import { Button } from "@/components/ui/Button";
import type { Checks } from "@/lib/api/types";
import { TODAY_TEXT } from "../strings";

interface InlineChecksProps {
  checks: Checks;
  lead: boolean;
  pending: boolean;
  onSave: (checks: Checks) => void;
}

export function InlineChecks({ checks, lead, pending, onSave }: InlineChecksProps) {
  const [draft, setDraft] = useState<Checks>(() => withAllChecks(checks));
  return (
    <div className="-mx-4.5 flex flex-col">
      <CheckToggles checks={draft} onChange={(key, on) => setDraft((current) => ({ ...current, [key]: on }))} />
      <div className="flex justify-end border-t border-hairline px-4 pt-3">
        <Button size="sm" variant={lead ? "primary" : "secondary"} pending={pending} onClick={() => onSave(draft)}>
          {TODAY_TEXT.checklist.actions.saveChecks}
        </Button>
      </div>
    </div>
  );
}
