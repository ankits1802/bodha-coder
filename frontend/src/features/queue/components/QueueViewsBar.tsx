"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { MenuButton } from "@/components/ui/MenuButton";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { currentFilters, matchingView, viewChanges, viewChoices } from "../queueViews";
import { QUEUE_TEXT } from "../strings";
import type { QueueFilters } from "../useQueueFilters";
import { useQueueViews } from "../useQueueViews";
import { SaveViewDialog } from "./SaveViewDialog";

export function QueueViewsBar({ filters }: { filters: QueueFilters }) {
  const words = QUEUE_TEXT.views;
  const views = useQueueViews();
  const [saving, setSaving] = useState(false);
  const current = currentFilters(filters);
  const choices = views.views ? viewChoices(views.views) : [];
  const saved = views.views?.saved ?? [];

  async function save(name: string): Promise<void> {
    if (await views.save(name, current)) setSaving(false);
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {choices.length > 0 ? (
        <SegmentedControl
          label={words.label}
          size="sm"
          value={matchingView(choices, current)}
          segments={choices.map((choice) => ({ value: choice.value, label: choice.label }))}
          onChange={(value) => {
            const chosen = choices.find((choice) => choice.value === value);
            if (chosen) filters.update(viewChanges(chosen.filters));
          }}
        />
      ) : null}
      <Button
        size="sm"
        variant="plain"
        onClick={() => {
          views.clearSaveError();
          setSaving(true);
        }}
      >
        {words.save}
      </Button>
      {saved.length > 0 ? (
        <MenuButton
          label={words.manage}
          items={saved.map((view) => ({
            key: view.id,
            label: words.remove(view.name),
            tone: "danger",
            onSelect: () => void views.remove(view.id),
          }))}
        />
      ) : null}
      {views.removeError ? (
        <span role="alert" className="text-footnote text-bad-text">
          {views.removeError}
        </span>
      ) : null}
      {saving ? (
        <SaveViewDialog open pending={views.saving} error={views.saveError} onSave={(name) => void save(name)} onClose={() => setSaving(false)} />
      ) : null}
    </div>
  );
}
