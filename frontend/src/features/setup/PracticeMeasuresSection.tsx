"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { useAction } from "@/hooks/useAction";
import { retirePracticeMeasure } from "@/lib/api/practice";
import type { PracticeMeasure } from "@/lib/api/types";
import { PracticeMeasureDialog } from "./PracticeMeasureDialog";
import { PracticeMeasureList } from "./PracticeMeasureList";
import { PRACTICE_MEASURE_TEXT } from "./strings";

interface PracticeMeasuresSectionProps {
  measures: PracticeMeasure[];
  chosen: Set<string>;
  onToggle: (key: string, on: boolean) => void;
  onChanged: () => void;
}

const words = PRACTICE_MEASURE_TEXT.confirm;

export function PracticeMeasuresSection({ measures, chosen, onToggle, onChanged }: PracticeMeasuresSectionProps) {
  const [editing, setEditing] = useState<PracticeMeasure | "new" | null>(null);
  const [retiring, setRetiring] = useState<PracticeMeasure | null>(null);
  const retire = useAction((measure: PracticeMeasure) => retirePracticeMeasure(measure.key, measure.version));

  async function confirmRetire(): Promise<void> {
    if (!retiring) return;
    const outcome = await retire.run(retiring);
    if (!outcome.ok) return;
    onToggle(retiring.key, false);
    setRetiring(null);
    onChanged();
  }

  function saved(measure: PracticeMeasure): void {
    if (editing === "new") onToggle(measure.key, true);
    setEditing(null);
    onChanged();
  }

  return (
    <>
      <PracticeMeasureList
        measures={measures}
        chosen={chosen}
        onToggle={onToggle}
        onAdd={() => setEditing("new")}
        onEdit={setEditing}
        onRetire={(measure) => {
          retire.clearError();
          setRetiring(measure);
        }}
      />
      {editing !== null ? (
        <PracticeMeasureDialog measure={editing === "new" ? null : editing} onClose={() => setEditing(null)} onSaved={saved} />
      ) : null}
      <ConfirmDialog
        open={retiring !== null}
        title={retiring ? words.title(retiring.name) : ""}
        confirmLabel={words.action}
        cancelLabel={words.cancel}
        destructive
        pending={retire.pending}
        error={retire.error}
        onConfirm={() => void confirmRetire()}
        onClose={() => setRetiring(null)}
      />
    </>
  );
}
