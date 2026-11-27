"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { adoptSignature, draftSignature } from "@/lib/api/signatures";
import type { SignatureView } from "@/lib/api/types";
import { SignatureFields } from "./SignatureFields";
import { draftFrom } from "./signatureImage";
import { SignaturePicture } from "./SignaturePicture";
import { SIGNATURE_TEXT } from "./strings";
import { useSignatureEntry } from "./useSignatureEntry";

interface SignatureSetupProps {
  defaultName: string;
  onAdopted: (signature: SignatureView) => void;
}

export function SignatureSetup({ defaultName, onAdopted }: SignatureSetupProps) {
  const state = useSignatureEntry(defaultName);
  const [draft, setDraft] = useState<SignatureView | null>(null);
  const check = useAction(async () => draftSignature(await draftFrom(state.entry)));
  const adopt = useAction(adoptSignature);

  async function save(): Promise<void> {
    const outcome = await check.run();
    if (outcome.ok) setDraft(outcome.value);
  }

  async function confirm(chosen: SignatureView): Promise<void> {
    const outcome = await adopt.run(chosen.id);
    if (outcome.ok && outcome.value.signature) onAdopted(outcome.value.signature);
  }

  if (draft) {
    return (
      <div className="flex flex-col gap-3">
        <SignaturePicture src={draft.image} alt={SIGNATURE_TEXT.preview(draft.typed_name)} />
        {adopt.error ? <InlineAlert tone="bad">{adopt.error}</InlineAlert> : null}
        <div className="flex justify-end gap-2">
          <Button variant="plain" disabled={adopt.pending} onClick={() => setDraft(null)}>
            {SIGNATURE_TEXT.redo}
          </Button>
          <Button variant="primary" pending={adopt.pending} onClick={() => void confirm(draft)}>
            {SIGNATURE_TEXT.adopt}
          </Button>
        </div>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <SignatureFields state={state} disabled={check.pending} />
      {check.error ? <InlineAlert tone="bad">{check.error}</InlineAlert> : null}
      <div className="flex justify-end">
        <Button variant="primary" disabled={!state.ready} pending={check.pending} onClick={() => void save()}>
          {SIGNATURE_TEXT.continue}
        </Button>
      </div>
    </div>
  );
}
