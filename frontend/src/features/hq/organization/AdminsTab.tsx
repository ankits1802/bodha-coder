"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { MemberIdentity, MemberLastSeen, MemberTwoStep } from "@/components/shared/MemberCells";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { TextButton } from "@/components/ui/TextButton";
import { useAction } from "@/hooks/useAction";
import { removeOrganizationAdmin } from "@/lib/api/hqOrganizations";
import type { HqOrganization, HqOrganizationAdmin } from "@/lib/api/types";
import { HQ_TEXT } from "../strings";
import { AddOrganizationAdminDialog } from "./AddOrganizationAdminDialog";

const words = HQ_TEXT.organization.admins;
const notices = HQ_TEXT.organization.notices;

function memberFacts(admin: HqOrganizationAdmin) {
  return { ...admin, status: "active" as const };
}

function AdminsTable({ admins, onRemove }: { admins: HqOrganizationAdmin[]; onRemove: ((admin: HqOrganizationAdmin) => void) | null }) {
  return (
    <Table label={words.tableLabel} minWidth="md">
      <thead>
        <tr>
          <Th>{words.columns.name}</Th>
          <Th>{words.columns.twoStep}</Th>
          <Th>{words.columns.lastActive}</Th>
          <Th className="w-24">
            <span className="sr-only">{HQ_TEXT.practices.columns.more}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {admins.map((admin) => (
          <Tr key={admin.id}>
            <Td>
              <MemberIdentity member={memberFacts(admin)} isSelf={false} />
            </Td>
            <Td>
              <MemberTwoStep member={memberFacts(admin)} />
            </Td>
            <Td>
              <MemberLastSeen member={memberFacts(admin)} />
            </Td>
            <Td className="text-right">
              {onRemove ? (
                <TextButton aria-label={words.removeFor(admin.name)} onClick={() => onRemove(admin)}>
                  {words.remove}
                </TextButton>
              ) : null}
            </Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}

interface AdminsTabProps {
  organization: HqOrganization;
  admins: HqOrganizationAdmin[];
  onChanged: (notice: string) => void;
}

export function AdminsTab({ organization, admins, onChanged }: AdminsTabProps) {
  const editable = organization.status === "active";
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<HqOrganizationAdmin | null>(null);
  const remove = useAction(removeOrganizationAdmin);

  async function confirmRemove(admin: HqOrganizationAdmin): Promise<void> {
    const outcome = await remove.run(organization.id, admin.id);
    if (!outcome.ok) return;
    setRemoving(null);
    onChanged(notices.adminRemoved(admin.name));
  }

  return (
    <Panel aria-label={words.tableLabel}>
      <PanelHeader title={words.tableLabel} actions={editable ? <Button onClick={() => setAdding(true)}>{words.add}</Button> : null} />
      {admins.length === 0 ? <EmptyState title={words.empty} /> : <AdminsTable admins={admins} onRemove={editable ? setRemoving : null} />}
      {adding ? (
        <AddOrganizationAdminDialog
          organization={organization}
          onClose={() => setAdding(false)}
          onAdded={(email) => {
            setAdding(false);
            onChanged(notices.adminAdded(email));
          }}
        />
      ) : null}
      <ConfirmDialog
        open={removing !== null}
        title={removing ? words.removeTitle(removing.name) : ""}
        confirmLabel={words.remove}
        cancelLabel={HQ_TEXT.organization.confirm.cancel}
        destructive
        pending={remove.pending}
        error={remove.error}
        onConfirm={() => (removing ? void confirmRemove(removing) : undefined)}
        onClose={() => setRemoving(null)}
      />
    </Panel>
  );
}
