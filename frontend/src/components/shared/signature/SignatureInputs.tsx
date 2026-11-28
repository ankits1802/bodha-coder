"use client";

import { useRef, useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { messageOf } from "@/lib/api/errors";
import { uploadedImage } from "./signatureImage";
import { SignaturePicture } from "./SignaturePicture";
import { SIGNATURE_TEXT } from "./strings";

export function TypedSignature({ name }: { name: string }) {
  const text = name.trim();
  return (
    <SignaturePicture src={null} alt={SIGNATURE_TEXT.typedPreview(text)}>
      <p role="img" aria-label={SIGNATURE_TEXT.typedPreview(text)} className="m-0 truncate px-4 font-signature text-large-title text-ink">
        {text}
      </p>
    </SignaturePicture>
  );
}

interface UploadSignatureProps {
  upload: string | null;
  disabled: boolean;
  onChange: (upload: string | null) => void;
}

export function UploadSignature({ upload, disabled, onChange }: UploadSignatureProps) {
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  async function choose(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(null);
    try {
      onChange(await uploadedImage(file));
    } catch (caught) {
      onChange(null);
      setError(messageOf(caught));
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <SignaturePicture src={upload} alt={SIGNATURE_TEXT.photo} />
      <div className="flex justify-end">
        <Button size="sm" disabled={disabled} onClick={() => input.current?.click()}>
          {SIGNATURE_TEXT.choosePhoto}
        </Button>
        <input
          ref={input}
          type="file"
          accept="image/*"
          aria-label={SIGNATURE_TEXT.photo}
          tabIndex={-1}
          className="sr-only"
          onChange={(event) => void choose(event)}
        />
      </div>
      {error ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
    </div>
  );
}
