"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import type { QueueRow, User } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { bulkAbilities } from "../queueRules";
import { QUEUE_TEXT } from "../strings";
import type { QueueActions } from "../useQueueActions";
import { AssignDialog } from "./AssignDialog";
import { BulkBar } from "./BulkBar";

type OpenDialog = "assign" | "delete" | null;

interface BulkActionsProps {
  member: User;
  rows: QueueRow[];
  actions: QueueActions;
  onClear: () => void;
}

export function BulkActions({ member, rows, actions, onClear }: BulkActionsProps) {
  const [dialog, setDialog] = useState<OpenDialog>(null);
  const ids = rows.map((row) => row.id);
  const amount = formatCount(rows.length);
  const show = (next: OpenDialog) => {
    actions.clearDialogErrors();
    setDialog(next);
  };

  async function assignTo(userId: string | null): Promise<void> {
    if (await actions.assignSelected(ids, userId)) setDialog(null);
  }

  async function remove(): Promise<void> {
    if (await actions.deleteSelected(ids)) setDialog(null);
  }

  return (
    <>
      <BulkBar
        count={rows.length}
        abilities={bulkAbilities(rows, member)}
        pending={actions.approving}
        onClear={onClear}
        onApprove={() => void actions.approveSelected(ids)}
        onAssign={() => show("assign")}
        onDelete={() => show("delete")}
      />
      <AssignDialog
        open={dialog === "assign"}
        count={rows.length}
        member={member}
        pending={actions.assigning}
        error={actions.assignError}
        onClose={() => setDialog(null)}
        onAssign={(userId) => void assignTo(userId)}
      />
      <ConfirmDialog
        open={dialog === "delete"}
        destructive
        title={QUEUE_TEXT.deleteTitle(rows.length, amount)}
        description={QUEUE_TEXT.deleteDescription}
        confirmLabel={QUEUE_TEXT.deleteConfirm(rows.length, amount)}
        cancelLabel={QUEUE_TEXT.keep}
        pending={actions.deleting}
        error={actions.deleteError}
        onConfirm={() => void remove()}
        onClose={() => setDialog(null)}
      />
    </>
  );
}
