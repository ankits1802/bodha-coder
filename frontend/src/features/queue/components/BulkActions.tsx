"use client";

import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import type { QueueRow, User } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { bulkAbilities } from "../queueRules";
import { QUEUE_TEXT } from "../strings";
import type { QueueActions } from "../useQueueActions";
import { AssignDialog } from "./AssignDialog";
import { BulkBar } from "./BulkBar";

export type BulkDialog = "assign" | "delete" | null;

interface BulkActionsProps {
  member: User;
  rows: QueueRow[];
  actions: QueueActions;
  dialog: BulkDialog;
  onDialog: (dialog: BulkDialog) => void;
  onClear: () => void;
}

export function BulkActions({ member, rows, actions, dialog, onDialog, onClear }: BulkActionsProps) {
  const ids = rows.map((row) => row.id);
  const amount = formatCount(rows.length);
  const show = (next: BulkDialog) => {
    actions.clearDialogErrors();
    onDialog(next);
  };

  async function assignTo(userId: string | null): Promise<void> {
    if (await actions.assignSelected(ids, userId)) onDialog(null);
  }

  async function remove(): Promise<void> {
    if (await actions.deleteSelected(ids)) onDialog(null);
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
        onClose={() => onDialog(null)}
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
        onClose={() => onDialog(null)}
      />
    </>
  );
}
