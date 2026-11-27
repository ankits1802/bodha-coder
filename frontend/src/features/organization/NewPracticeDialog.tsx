"use client";

import { useState } from "react";
import { AgreementCheck } from "@/components/shared/agreement/AgreementCheck";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { loadedOptions, useSignInOptions } from "@/hooks/useSignInOptions";
import { addLocation } from "@/lib/api/organizations";
import { TIME_ZONES, TIME_ZONE_LABELS, preferredTimeZone } from "@/lib/timeZones";
import { ORGANIZATION_TEXT } from "./strings";

interface NewPracticeDialogProps {
  organizationId: string;
  onClose: () => void;
  onAdded: (name: string) => void;
}

const words = ORGANIZATION_TEXT.location;
const NAME_MIN = 2;
const ZONE_OPTIONS = TIME_ZONES.map((zone) => ({ value: zone, label: TIME_ZONE_LABELS[zone] ?? zone }));

export function NewPracticeDialog({ organizationId, onClose, onAdded }: NewPracticeDialogProps) {
  const [name, setName] = useState("");
  const [timeZone, setTimeZone] = useState(() => preferredTimeZone());
  const [agreed, setAgreed] = useState(false);
  const [checked, setChecked] = useState(false);
  const add = useAction(addLocation);
  const options = loadedOptions(useSignInOptions())?.signup ?? null;
  const trimmed = name.trim();
  const nameError = checked && trimmed.length < NAME_MIN ? words.nameNeeded : null;
  const agreementError = checked && !agreed ? words.agreementNeeded : null;

  async function submit(): Promise<void> {
    setChecked(true);
    if (trimmed.length < NAME_MIN || !agreed) return;
    if ((await add.run(organizationId, { name: trimmed, time_zone: timeZone, agreed: true })).ok) onAdded(trimmed);
  }

  const footer = (
    <>
      <Button variant="plain" onClick={onClose}>
        {words.cancel}
      </Button>
      <Button variant="primary" pending={add.pending} onClick={() => void submit()}>
        {words.create}
      </Button>
    </>
  );

  return (
    <Dialog open onClose={onClose} title={words.title} footer={footer}>
      <div className="flex flex-col gap-4">
        <Field label={words.name} error={nameError}>
          {(control) => (
            <Input {...control} autoComplete="organization" value={name} onChange={(event) => setName(event.target.value)} />
          )}
        </Field>
        <Field label={words.timeZone}>
          {(control) => <Select {...control} value={timeZone} options={ZONE_OPTIONS} onChange={setTimeZone} />}
        </Field>
        {options ? <AgreementCheck options={options} checked={agreed} error={agreementError} onChange={setAgreed} /> : null}
        {add.error ? <InlineAlert tone="bad">{add.error}</InlineAlert> : null}
      </div>
    </Dialog>
  );
}
