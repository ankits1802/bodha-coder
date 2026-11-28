"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { useAction } from "@/hooks/useAction";
import type { MipsOverview } from "@/lib/api/types";
import { MeasureList } from "./MeasureList";
import { chosenIds, initialChoice, initialMode, saveMeasureList, type MipsMode } from "./mipsModel";
import { PracticeMeasuresSection } from "./PracticeMeasuresSection";
import { MIPS_TEXT } from "./strings";

interface MipsEditorProps {
  overview: MipsOverview;
  onReload: () => void;
}

type Feedback = "saved" | "conflict" | "none-chosen" | null;

export function MipsEditor({ overview, onReload }: MipsEditorProps) {
  const [mode, setMode] = useState<MipsMode>(() => initialMode(overview));
  const [chosen, setChosen] = useState<Set<string>>(() => initialChoice(overview));
  const [feedback, setFeedback] = useState<Feedback>(null);
  const save = useAction(saveMeasureList);
  const custom = mode === "custom";

  function toggle(id: string, on: boolean): void {
    setFeedback(null);
    setChosen((current) => {
      const next = new Set(current);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  async function submit(): Promise<void> {
    const ids = custom ? chosenIds(overview, chosen) : [];
    if (custom && ids.length === 0) {
      setFeedback("none-chosen");
      return;
    }
    const outcome = await save.run(ids, overview.measure_ids);
    if (!outcome.ok) return;
    setFeedback(outcome.value);
    if (outcome.value === "saved") onReload();
  }

  return (
    <div className="flex flex-col gap-3 pb-4">
      <div className="px-4">
        <SegmentedControl<MipsMode>
          label={MIPS_TEXT.modeLabel}
          value={mode}
          onChange={(next) => {
            setFeedback(null);
            setMode(next);
          }}
          segments={[
            { value: "standard", label: MIPS_TEXT.standard },
            { value: "custom", label: MIPS_TEXT.custom },
          ]}
        />
      </div>
      <MeasureList legend={MIPS_TEXT.standardGroup} measures={overview.standard} chosen={custom ? chosen : null} onToggle={toggle} />
      {custom ? <MeasureList legend={MIPS_TEXT.addableGroup} measures={overview.addable} chosen={chosen} onToggle={toggle} /> : null}
      {custom ? <PracticeMeasuresSection measures={overview.practice} chosen={chosen} onToggle={toggle} onChanged={onReload} /> : null}
      <div className="flex flex-wrap items-center justify-end gap-3 px-4">
        {feedback === "conflict" ? (
          <InlineAlert tone="warn" action={<Button size="sm" onClick={onReload}>{MIPS_TEXT.reload}</Button>}>
            {MIPS_TEXT.conflict}
          </InlineAlert>
        ) : null}
        {feedback === "none-chosen" ? <InlineAlert tone="bad">{MIPS_TEXT.noneChosen}</InlineAlert> : null}
        {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
        {feedback === "saved" ? (
          <span role="status" className="text-subhead text-secondary">
            {MIPS_TEXT.saved}
          </span>
        ) : null}
        <Button variant="primary" pending={save.pending} onClick={() => void submit()}>
          {MIPS_TEXT.save}
        </Button>
      </div>
    </div>
  );
}
