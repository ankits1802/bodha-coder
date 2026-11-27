"use client";

import { useAction } from "@/hooks/useAction";
import { closeOrganization, purgeOrganization, renewOrganization } from "@/lib/api/hqOrganizations";
import type { HqOrganization } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { ORGANIZATION_TIME_ZONE } from "../organizationStatus";
import { OrganizationDialog } from "../organizations/OrganizationDialog";
import type { TypedActionKind } from "../practices/practiceActions";
import { RenewDialog } from "../practices/RenewDialog";
import { TypedNameDialog, type TypedActionWords } from "../practices/TypedNameDialog";
import { HQ_TEXT } from "../strings";

export type OrganizationDialogKind = "renew" | "edit" | TypedActionKind;

const confirm = HQ_TEXT.organization.confirm;
const notices = HQ_TEXT.organization.notices;
const KIND_WORDS: Record<TypedActionKind, TypedActionWords> = {
  close: { title: confirm.close, description: confirm.closeDescription, action: confirm.closeAction },
  purge: { title: confirm.purge, description: confirm.purgeDescription, action: confirm.purgeAction },
};

async function runTyped(kind: TypedActionKind, organization: HqOrganization, typedName: string): Promise<string> {
  if (kind === "close") {
    await closeOrganization(organization.id, typedName);
    return notices.closed(organization.name);
  }
  const { rows_removed } = await purgeOrganization(organization.id, typedName);
  return notices.purged(organization.name, formatCount(rows_removed));
}

interface OrganizationDialogsProps {
  kind: OrganizationDialogKind;
  organization: HqOrganization;
  onDone: (notice: string) => void;
  onClose: () => void;
}

export function OrganizationDialogs({ kind, organization, onDone, onClose }: OrganizationDialogsProps) {
  const typed = useAction(runTyped);
  if (kind === "renew") {
    const subject = { ...organization, time_zone: ORGANIZATION_TIME_ZONE };
    return <RenewDialog subject={subject} renewOne={renewOrganization} onDone={onDone} onClose={onClose} />;
  }
  if (kind === "edit") {
    return <OrganizationDialog organization={organization} onClose={onClose} onSaved={(name) => onDone(notices.saved(name))} />;
  }
  return (
    <TypedNameDialog
      kind={kind}
      subject={organization}
      kindWords={KIND_WORDS}
      pending={typed.pending}
      error={typed.error}
      onConfirm={(typedName) =>
        void typed.run(kind, organization, typedName).then((outcome) => (outcome.ok ? onDone(outcome.value) : undefined))
      }
      onClose={onClose}
    />
  );
}
