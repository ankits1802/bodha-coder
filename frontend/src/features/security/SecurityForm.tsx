"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { refreshSession } from "@/lib/api/client";
import { saveSecurity } from "@/lib/api/practice";
import type { AccessLogYears, IdleMinutes, PracticeRole, SecuritySettings } from "@/lib/api/types";
import { PRACTICE_ROLES } from "@/lib/roles";
import { RolesPicker } from "./RolesPicker";
import { SECURITY_TEXT } from "./strings";

const IDLE_CHOICES: readonly IdleMinutes[] = [5, 10, 15, 30];
const YEAR_CHOICES: readonly AccessLogYears[] = [6, 7, 8, 9, 10];
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
  const [years, setYears] = useState<AccessLogYears>(settings.access_log_years);
  const [saved, setSaved] = useState(false);
  const save = useAction(saveAndRefresh);
  const chosen = PRACTICE_ROLES.filter((role) => roles.has(role));
  const dirty =
    chosen.join() !== PRACTICE_ROLES.filter((role) => settings.mfa_roles.includes(role)).join() ||
    idle !== settings.idle_minutes ||
    years !== settings.access_log_years;

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
    const outcome = await save.run({ mfa_roles: chosen, idle_minutes: idle, access_log_years: years });
    if (!outcome.ok) return;
    setSaved(true);
    onSaved();
  }

  return (
    <>
      <RolesPicker value={roles} onToggle={toggleRole} />
      <div className={ROW}>
        <span>{SECURITY_TEXT.idle}</span>
        <Select
          variant="filter"
          label={SECURITY_TEXT.idle}
          value={String(idle)}
          options={IDLE_CHOICES.map((minutes) => ({ value: String(minutes), label: SECURITY_TEXT.minutes(minutes) }))}
          onChange={(next) => {
            setSaved(false);
            setIdle(Number(next) as IdleMinutes);
          }}
        />
      </div>
      <div className={ROW}>
        <span>{SECURITY_TEXT.keepLog}</span>
        <Select
          variant="filter"
          label={SECURITY_TEXT.keepLog}
          value={String(years)}
          options={YEAR_CHOICES.map((count) => ({ value: String(count), label: SECURITY_TEXT.years(count) }))}
          onChange={(next) => {
            setSaved(false);
            setYears(Number(next) as AccessLogYears);
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
