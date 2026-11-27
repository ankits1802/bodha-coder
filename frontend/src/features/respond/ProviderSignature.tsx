import { SignatureFields } from "@/components/shared/signature/SignatureFields";
import { SignaturePicture } from "@/components/shared/signature/SignaturePicture";
import { SIGNATURE_TEXT } from "@/components/shared/signature/strings";
import { Button } from "@/components/ui/Button";
import { RESPOND_TEXT } from "./strings";
import type { ProviderSigning } from "./useProviderSigning";

interface ProviderSignatureProps {
  signing: ProviderSigning;
  disabled: boolean;
}

export function ProviderSignature({ signing, disabled }: ProviderSignatureProps) {
  const { remembered } = signing;
  if (signing.useSaved && remembered) {
    return (
      <div className="flex flex-col gap-2">
        <SignaturePicture src={remembered.image} alt={SIGNATURE_TEXT.preview(remembered.typed_name)} />
        <div className="flex justify-end">
          <Button variant="plain" size="sm" disabled={disabled} onClick={() => signing.setUseSaved(false)}>
            {RESPOND_TEXT.newSignature}
          </Button>
        </div>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <SignatureFields state={signing.entry} disabled={disabled} />
      <label className="flex cursor-pointer items-center gap-3 text-body">
        <input
          type="checkbox"
          checked={signing.remember}
          disabled={disabled}
          onChange={(event) => signing.setRemember(event.target.checked)}
          className="size-5 flex-none accent-label"
        />
        {RESPOND_TEXT.rememberSignature}
      </label>
      {remembered ? (
        <div className="flex justify-end">
          <Button variant="plain" size="sm" disabled={disabled} onClick={() => signing.setUseSaved(true)}>
            {RESPOND_TEXT.savedSignature}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
