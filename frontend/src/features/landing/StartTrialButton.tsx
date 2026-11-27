import { ButtonLink } from "@/components/ui/ButtonLink";
import type { ButtonSize } from "@/components/ui/buttonStyles";
import { SIGN_UP_PATH } from "@/lib/api/auth";

export function StartTrialButton({ size = "lg", label }: { size?: ButtonSize; label: string }) {
  return (
    <ButtonLink href={SIGN_UP_PATH} variant="primary" size={size}>
      {label}
    </ButtonLink>
  );
}
