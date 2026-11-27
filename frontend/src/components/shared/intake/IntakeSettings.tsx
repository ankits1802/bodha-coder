"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { Select } from "@/components/ui/Select";
import { Toggle } from "@/components/ui/Toggle";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getIntake, saveIntake } from "@/lib/api/intake";
import type { IntakeView, Place, Provider } from "@/lib/api/types";
import { getPlaces, getProviders } from "@/lib/api/uploads";
import { VISIT_TYPES } from "@/lib/labels";
import { FolderRows } from "./FolderRows";
import { draftFrom, hasProblems, nextRowId, problemsOf, settingsFrom, type IntakeDraft } from "./intakeForm";
import { INTAKE_TEXT } from "./strings";

interface IntakeData {
  view: IntakeView;
  providers: Provider[];
  places: Place[];
}

const REMOTE_TEXT = { loading: INTAKE_TEXT.loading, empty: INTAKE_TEXT.loading, retry: INTAKE_TEXT.retry };

async function loadIntake(): Promise<IntakeData> {
  const [view, providers, places] = await Promise.all([getIntake(), getProviders(), getPlaces()]);
  return { view, providers, places };
}

function IntakeForm({ data }: { data: IntakeData }) {
  const [draft, setDraft] = useState<IntakeDraft>(() => draftFrom(data.view));
  const [saved, setSaved] = useState(false);
  const save = useAction(saveIntake);
  const problems = problemsOf(draft);
  const visitTypes: readonly string[] = VISIT_TYPES.some((type) => type === draft.visitType) ? VISIT_TYPES : [draft.visitType, ...VISIT_TYPES];

  function change(next: Partial<IntakeDraft>): void {
    setSaved(false);
    setDraft((current) => ({ ...current, ...next }));
  }

  async function submit(): Promise<void> {
    const outcome = await save.run(settingsFrom(draft));
    if (!outcome.ok) return;
    setDraft(draftFrom(outcome.value));
    setSaved(true);
  }

  return (
    <>
      <div className="flex h-12 items-center justify-between gap-3 border-t border-hairline px-4 text-body">
        <span>{INTAKE_TEXT.enabled}</span>
        <Toggle label={INTAKE_TEXT.enabled} checked={draft.enabled} onChange={(enabled) => change({ enabled })} />
      </div>
      <div className="flex flex-col gap-4 border-t border-hairline px-4 py-4">
        <div className="flex flex-col gap-1.5">
          <span className="text-subhead font-medium text-label">{INTAKE_TEXT.watched}</span>
          <span className="text-body break-all text-secondary tabular-nums select-all">{data.view.watched_prefix}</span>
        </div>
        <Field label={INTAKE_TEXT.place} error={problems.place}>
          {(control) => (
            <Select
              {...control}
              value={draft.placeCode}
              options={[
                { value: "", label: INTAKE_TEXT.choosePlace },
                ...data.places.map((place) => ({ value: place.code, label: INTAKE_TEXT.placeOption(place.code, place.name) })),
              ]}
              onChange={(placeCode) => change({ placeCode })}
              className="max-w-80"
            />
          )}
        </Field>
        <Field label={INTAKE_TEXT.visitType}>
          {(control) => (
            <Select
              {...control}
              value={draft.visitType}
              options={visitTypes.map((type) => ({ value: type, label: type }))}
              onChange={(visitType) => change({ visitType })}
              className="max-w-80"
            />
          )}
        </Field>
        <div className="flex flex-col gap-2">
          <span className="text-subhead font-medium text-label">{INTAKE_TEXT.folders}</span>
          <FolderRows
            rows={draft.folders}
            providers={data.providers}
            problems={problems.folders}
            onChange={(row) => change({ folders: draft.folders.map((item) => (item.id === row.id ? row : item)) })}
            onRemove={(rowId) => change({ folders: draft.folders.filter((item) => item.id !== rowId) })}
          />
          {problems.general ? <span className="text-footnote text-bad-text">{problems.general}</span> : null}
          <Button
            size="sm"
            className="self-start"
            onClick={() => change({ folders: [...draft.folders, { id: nextRowId(draft.folders), folder: "", providerId: "" }] })}
          >
            {INTAKE_TEXT.addFolder}
          </Button>
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-hairline px-4 py-3">
        {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
        {saved ? (
          <span role="status" className="text-subhead text-secondary">
            {INTAKE_TEXT.saved}
          </span>
        ) : null}
        <Button pending={save.pending} disabled={hasProblems(problems)} onClick={() => void submit()}>
          {INTAKE_TEXT.save}
        </Button>
      </div>
    </>
  );
}

export function IntakeSettings() {
  const intake = useRemote("practice-intake", loadIntake);
  return (
    <Panel aria-label={INTAKE_TEXT.title}>
      <PanelHeader title={INTAKE_TEXT.title} />
      <RemoteView state={intake.state} text={REMOTE_TEXT} onRetry={intake.reload}>
        {(data) => <IntakeForm data={data} />}
      </RemoteView>
    </Panel>
  );
}
