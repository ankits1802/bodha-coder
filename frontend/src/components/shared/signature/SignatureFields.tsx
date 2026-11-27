"use client";

import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { SegmentedControl, type Segment } from "@/components/ui/SegmentedControl";
import type { SignatureSource } from "@/lib/api/types";
import { SignaturePad } from "./SignaturePad";
import { TypedSignature, UploadSignature } from "./SignatureInputs";
import { SIGNATURE_TEXT } from "./strings";
import type { SignatureEntryState } from "./useSignatureEntry";

const SOURCES: readonly SignatureSource[] = ["drawn", "typed", "uploaded"];
const MODES: Segment<SignatureSource>[] = SOURCES.map((value) => ({ value, label: SIGNATURE_TEXT.modes[value] }));

interface SignatureFieldsProps {
  state: SignatureEntryState;
  disabled?: boolean;
}

export function SignatureFields({ state, disabled = false }: SignatureFieldsProps) {
  const { entry, change } = state;
  return (
    <div className="flex flex-col gap-3">
      <SegmentedControl label={SIGNATURE_TEXT.modesLabel} value={entry.mode} segments={MODES} onChange={(mode) => change({ mode })} />
      <Field label={SIGNATURE_TEXT.fullName}>
        {(control) => (
          <Input
            {...control}
            autoComplete="name"
            value={entry.name}
            disabled={disabled}
            onChange={(event) => change({ name: event.target.value })}
          />
        )}
      </Field>
      {entry.mode === "drawn" ? <SignaturePad strokes={entry.strokes} disabled={disabled} onChange={(strokes) => change({ strokes })} /> : null}
      {entry.mode === "typed" ? <TypedSignature name={entry.name} /> : null}
      {entry.mode === "uploaded" ? <UploadSignature upload={entry.upload} disabled={disabled} onChange={(upload) => change({ upload })} /> : null}
    </div>
  );
}
