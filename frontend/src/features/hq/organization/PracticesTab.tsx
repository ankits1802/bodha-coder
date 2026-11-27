"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { useAction } from "@/hooks/useAction";
import { detachPractice, setCombinedBilling } from "@/lib/api/hqOrganizations";
import type { HqOrganization, OrganizationPracticeRow } from "@/lib/api/types";
import { HQ_TEXT } from "../strings";
import { AttachPracticeDialog } from "./AttachPracticeDialog";
import { OrganizationPracticesTable } from "./OrganizationPracticesTable";

const words = HQ_TEXT.organization.practices;
const notices = HQ_TEXT.organization.notices;

interface PracticesTabProps {
  organization: HqOrganization;
  practices: OrganizationPracticeRow[];
  onChanged: (notice: string | null) => void;
}

export function PracticesTab({ organization, practices, onChanged }: PracticesTabProps) {
  const editable = organization.status === "active";
  const [attaching, setAttaching] = useState(false);
  const [removing, setRemoving] = useState<OrganizationPracticeRow | null>(null);
  const combine = useAction(setCombinedBilling);
  const detach = useAction(detachPractice);

  async function changeCombined(practice: OrganizationPracticeRow, combined: boolean): Promise<void> {
    const outcome = await combine.run(organization.id, practice.id, combined);
    if (outcome.ok) onChanged(null);
  }

  async function remove(practice: OrganizationPracticeRow): Promise<void> {
    const outcome = await detach.run(organization.id, practice.id);
    if (!outcome.ok) return;
    setRemoving(null);
    onChanged(notices.removed(practice.name));
  }

  return (
    <Panel aria-label={words.tableLabel}>
      <PanelHeader
        title={words.tableLabel}
        actions={editable ? <Button onClick={() => setAttaching(true)}>{words.add}</Button> : null}
      />
      {combine.error ? (
        <div className="px-4 pb-3">
          <InlineAlert tone="bad">{combine.error}</InlineAlert>
        </div>
      ) : null}
      {practices.length === 0 ? (
        <EmptyState title={words.empty} />
      ) : (
        <OrganizationPracticesTable
          practices={practices}
          editable={editable}
          busy={combine.pending}
          onCombined={(practice, combined) => void changeCombined(practice, combined)}
          onRemove={(practice) => {
            detach.clearError();
            setRemoving(practice);
          }}
        />
      )}
      {attaching ? (
        <AttachPracticeDialog
          organizationId={organization.id}
          onClose={() => setAttaching(false)}
          onAttached={(name) => {
            setAttaching(false);
            onChanged(notices.attached(name));
          }}
        />
      ) : null}
      <ConfirmDialog
        open={removing !== null}
        title={removing ? words.removeTitle(removing.name) : ""}
        confirmLabel={words.removeAction}
        cancelLabel={HQ_TEXT.organization.confirm.cancel}
        destructive
        pending={detach.pending}
        error={detach.error}
        onConfirm={() => (removing ? void remove(removing) : undefined)}
        onClose={() => setRemoving(null)}
      />
    </Panel>
  );
}
