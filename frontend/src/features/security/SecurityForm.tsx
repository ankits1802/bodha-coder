"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { FilterSelect } from "@/components/ui/FilterSelect";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Toggle } from "@/components/ui/Toggle";
import { useAction } from "@/hooks/useAction";
import { refreshSession } from "@/lib/api/client";
import { saveSecurity } from "@/lib/api/practice";
import type { IdleMinutes, PracticeRole, SecuritySettings } from "@/lib/api/types";
import { PRACTICE_ROLES } from "@/lib/roles";
import { RolesPicker } from "./RolesPicker";
import { SECURITY_TEXT } from "./strings";

const IDLE_CHOICES: readonly IdleMinutes[] = [5, 10, 15, 30];
const ROW = "flex min-h-13 items-center justify-between gap-4 border-t border-hairline px-4.5 text-body";

async function saveAndRefresh(settings: SecuritySettings): Promise<void> {
  await saveSecurity(settings);
  await refreshSession();
}

interface SecurityFormProps {
  settings: SecuritySettings;
  onSaved: () => void;
}

export function SecurityForm({ settings, onSaved }: SecurityFormProps) {
  const [roles, setRoles] = useState<Set<PracticeRole>>(() => new Set(settings.mfa_roles));
  const [idle, setIdle] = useState<IdleMinutes>(settings.idle_minutes);
  const [hidden, setHidden] = useState(settings.private_messages);
  const [saved, setSaved] = useState(false);
  const save = useAction(saveAndRefresh);
  const chosen = PRACTICE_ROLES.filter((role) => roles.has(role));
  const dirty =
    chosen.join() !== PRACTICE_ROLES.filter((role) => settings.mfa_roles.includes(role)).join() ||
    idle !== settings.idle_minutes ||
    hidden !== settings.private_messages;

  function toggleRole(role: PracticeRole, on: boolean): void {
    setSaved(false);
    setRoles((current) => {
      const next = new Set(current);
      if (on) next.add(role);
      else next.delete(role);
      return next;
    });
  }

  async function submit(): Promise<void> {
    const outcome = await save.run({ mfa_roles: chosen, idle_minutes: idle, private_messages: hidden });
    if (!outcome.ok) return;
    setSaved(true);
    onSaved();
  }

  return (
    <>
      <RolesPicker value={roles} onToggle={toggleRole} />
      <div className={ROW}>
        <span>{SECURITY_TEXT.idle}</span>
        <FilterSelect
          label={SECURITY_TEXT.idle}
          value={idle}
          onChange={(event) => {
            setSaved(false);
            setIdle(Number(event.target.value) as IdleMinutes);
          }}
        >
          {IDLE_CHOICES.map((minutes) => (
            <option key={minutes} value={minutes}>
              {SECURITY_TEXT.minutes(minutes)}
            </option>
          ))}
        </FilterSelect>
      </div>
      <div className={ROW}>
        <span>{SECURITY_TEXT.privateMessages}</span>
        <Toggle
          label={SECURITY_TEXT.privateMessages}
          checked={hidden}
          onChange={(on) => {
            setSaved(false);
            setHidden(on);
          }}
        />
      </div>
      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-hairline px-4.5 py-3">
        {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
        {saved && !dirty ? (
          <span role="status" className="text-subhead text-secondary">
            {SECURITY_TEXT.saved}
          </span>
        ) : null}
        <Button variant="primary" pending={save.pending} disabled={!dirty} onClick={() => void submit()}>
          {SECURITY_TEXT.save}
        </Button>
      </div>
    </>
  );
}
