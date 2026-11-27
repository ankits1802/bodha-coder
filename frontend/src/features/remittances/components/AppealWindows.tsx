"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getAppealDays, saveAppealDays } from "@/lib/api/remittances";
import type { AppealDays, PlanType } from "@/lib/api/types";
import { REMITTANCE_TEXT } from "../strings";

const PLAN_ORDER: readonly PlanType[] = ["medicare", "medicare_advantage", "medicaid", "commercial", "other"];
const MAX_DAYS = 730;
const REMOTE_TEXT = { loading: REMITTANCE_TEXT.loading, empty: REMITTANCE_TEXT.noLines, retry: REMITTANCE_TEXT.retry };

function isValidDays(text: string): boolean {
  const value = Number(text);
  return Number.isInteger(value) && value >= 1 && value <= MAX_DAYS;
}

function WindowsForm({ stored, onSaved }: { stored: AppealDays; onSaved: (days: AppealDays) => void }) {
  const [draft, setDraft] = useState<Record<PlanType, string>>(() => ({
    medicare: String(stored.medicare),
    medicare_advantage: String(stored.medicare_advantage),
    medicaid: String(stored.medicaid),
    commercial: String(stored.commercial),
    other: String(stored.other),
  }));
  const [saved, setSaved] = useState(false);
  const save = useAction(saveAppealDays);
  const valid = PLAN_ORDER.every((plan) => isValidDays(draft[plan]));
  const dirty = PLAN_ORDER.some((plan) => draft[plan] !== String(stored[plan]));

  async function submit(): Promise<void> {
    const days = Object.fromEntries(PLAN_ORDER.map((plan) => [plan, Number(draft[plan])])) as AppealDays;
    const outcome = await save.run(days);
    if (!outcome.ok) return;
    setSaved(true);
    onSaved(outcome.value);
  }

  return (
    <>
      {PLAN_ORDER.map((plan) => (
        <label key={plan} className="flex h-12 items-center justify-between gap-3 border-t border-hairline px-4 text-body">
          <span>{REMITTANCE_TEXT.planTypes[plan]}</span>
          <span className="flex items-center gap-2 text-secondary">
            <Input
              type="number"
              min={1}
              max={MAX_DAYS}
              inputMode="numeric"
              aria-label={REMITTANCE_TEXT.windowsLabel(REMITTANCE_TEXT.planTypes[plan])}
              aria-invalid={isValidDays(draft[plan]) ? undefined : true}
              value={draft[plan]}
              onChange={(event) => {
                setSaved(false);
                setDraft((current) => ({ ...current, [plan]: event.target.value }));
              }}
              className="w-24 text-right tabular-nums"
            />
            {REMITTANCE_TEXT.days}
          </span>
        </label>
      ))}
      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-hairline px-4 py-3">
        {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
        {saved && !dirty ? (
          <span role="status" className="text-subhead text-secondary">
            {REMITTANCE_TEXT.saved}
          </span>
        ) : null}
        <Button pending={save.pending} disabled={!dirty || !valid} onClick={() => void submit()}>
          {REMITTANCE_TEXT.save}
        </Button>
      </div>
    </>
  );
}

export function AppealWindows({ onSaved }: { onSaved: () => void }) {
  const windows = useRemote("appeal-days", getAppealDays);
  return (
    <Panel aria-label={REMITTANCE_TEXT.windowsTitle}>
      <PanelHeader title={REMITTANCE_TEXT.windowsTitle} />
      <RemoteView state={windows.state} text={REMOTE_TEXT} onRetry={windows.reload}>
        {(data) => (
          <WindowsForm
            stored={data}
            onSaved={(days) => {
              windows.replace(days);
              onSaved();
            }}
          />
        )}
      </RemoteView>
    </Panel>
  );
}
