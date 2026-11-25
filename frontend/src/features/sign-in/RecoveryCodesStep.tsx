import { RecoveryCodeList } from "@/components/shared/RecoveryCodeList";
import { Button } from "@/components/ui/Button";
import { SIGN_IN_TEXT } from "./strings";

interface RecoveryCodesStepProps {
  codes: readonly string[];
  onContinue: () => void;
}

export function RecoveryCodesStep({ codes, onContinue }: RecoveryCodesStepProps) {
  return (
    <div className="flex flex-col gap-5.5">
      <h2 className="m-0 text-center font-sans text-headline font-semibold tracking-snug">{SIGN_IN_TEXT.codesTitle}</h2>
      <RecoveryCodeList codes={codes} />
      <Button variant="primary" size="lg" className="w-full" onClick={onContinue}>
        {SIGN_IN_TEXT.continue}
      </Button>
    </div>
  );
}
