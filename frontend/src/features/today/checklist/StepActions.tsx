import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { setupSectionPath } from "@/lib/paths";
import { PLAN_PATH } from "@/lib/roles";
import { TODAY_TEXT } from "../strings";
import type { StepKey } from "./checklistModel";

interface StepActionsProps {
  step: StepKey;
  lead: boolean;
  pending: boolean;
  onInvite: () => void;
  onRecommended: () => void;
}

export function StepActions({ step, lead, pending, onInvite, onRecommended }: StepActionsProps) {
  const words = TODAY_TEXT.checklist.actions;
  const main = lead ? "primary" : "secondary";
  if (step === "providers") {
    return (
      <>
        <ButtonLink href={setupSectionPath("providers", "importProviders")} size="sm">
          {words.importProviders}
        </ButtonLink>
        <ButtonLink href={setupSectionPath("providers", "addProvider")} size="sm" variant={main}>
          {words.addProvider}
        </ButtonLink>
      </>
    );
  }
  if (step === "payers") {
    return (
      <ButtonLink href={setupSectionPath("payers", "addPayer")} size="sm" variant={main}>
        {words.addPayer}
      </ButtonLink>
    );
  }
  if (step === "invite") {
    return (
      <Button size="sm" variant={main} onClick={onInvite}>
        {words.invite}
      </Button>
    );
  }
  if (step === "security") {
    return (
      <Button size="sm" variant={main} pending={pending} onClick={onRecommended}>
        {words.recommended}
      </Button>
    );
  }
  if (step === "plan") {
    return (
      <ButtonLink href={PLAN_PATH} size="sm" variant={main}>
        {words.choosePlan}
      </ButtonLink>
    );
  }
  return null;
}
