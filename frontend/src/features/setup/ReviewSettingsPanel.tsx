"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { Toggle } from "@/components/ui/Toggle";
import { useAction } from "@/hooks/useAction";
import { saveReviewSettings } from "@/lib/api/practice";
import type { ReviewSettings } from "@/lib/api/types";
import { SETUP_TEXT } from "./strings";

const WORDS = SETUP_TEXT.review;

interface ReviewSettingsPanelProps {
  settings: ReviewSettings;
  onSaved: () => void;
}

export function ReviewSettingsPanel({ settings, onSaved }: ReviewSettingsPanelProps) {
  const [draft, setDraft] = useState<ReviewSettings>(settings);
  const [saved, setSaved] = useState(false);
  const save = useAction(saveReviewSettings);
  const dirty =
    draft.confirm_level_changes !== settings.confirm_level_changes ||
    draft.hold_until_confirmed !== settings.hold_until_confirmed;

  function change(next: ReviewSettings): void {
    setSaved(false);
    setDraft({ ...next, hold_until_confirmed: next.confirm_level_changes && next.hold_until_confirmed });
  }

  async function submit(): Promise<void> {
    const outcome = await save.run(draft);
    if (!outcome.ok) return;
    setDraft(outcome.value);
    setSaved(true);
    onSaved();
  }

  return (
    <Panel aria-label={WORDS.title}>
      <PanelHeader title={WORDS.title} />
      <div className="flex min-h-12 items-center justify-between gap-3 border-t border-hairline px-4 text-body">
        <span>{WORDS.confirm}</span>
        <Toggle
          label={WORDS.confirm}
          checked={draft.confirm_level_changes}
          onChange={(on) => change({ ...draft, confirm_level_changes: on })}
        />
      </div>
      <div className="flex min-h-12 items-center justify-between gap-3 border-t border-hairline px-4 text-body">
        <span className={draft.confirm_level_changes ? "" : "text-tertiary"}>{WORDS.hold}</span>
        <Toggle
          label={WORDS.hold}
          checked={draft.hold_until_confirmed}
          disabled={!draft.confirm_level_changes}
          onChange={(on) => change({ ...draft, hold_until_confirmed: on })}
        />
      </div>
      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-hairline px-4 py-3">
        {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
        {saved && !dirty ? (
          <span role="status" className="text-subhead text-secondary">
            {WORDS.saved}
          </span>
        ) : null}
        <Button pending={save.pending} disabled={!dirty} onClick={() => void submit()}>
          {WORDS.save}
        </Button>
      </div>
    </Panel>
  );
}
