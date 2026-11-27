"use client";

import { ReasonDialog } from "@/components/shared/ReasonDialog";
import type { QueueRow, User } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { VOID_REASON_MAX, VOID_REASON_MIN } from "@/lib/validation";
import { bulkAbilities } from "../queueRules";
import { QUEUE_TEXT } from "../strings";
import type { QueueActions } from "../useQueueActions";
import { AssignDialog } from "./AssignDialog";
import { BulkBar } from "./BulkBar";

export type BulkDialog = "assign" | "void" | null;

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

  return (
    <>
      <BulkBar
        count={rows.length}
        abilities={bulkAbilities(rows, member)}
        pending={actions.approving}
        onClear={onClear}
        onApprove={() => void actions.approveSelected(ids)}
        onAssign={() => show("assign")}
        onVoid={() => show("void")}
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
      {dialog === "void" ? (
        <ReasonDialog
          destructive
          text={{
            title: QUEUE_TEXT.voidTitle(rows.length, amount),
            reason: QUEUE_TEXT.voidReason,
            submit: QUEUE_TEXT.voidConfirm(rows.length, amount),
            cancel: QUEUE_TEXT.keep,
            invalid: QUEUE_TEXT.voidReasonTooShort,
          }}
          minLength={VOID_REASON_MIN}
          maxLength={VOID_REASON_MAX}
          onClose={() => onDialog(null)}
          onDone={() => onDialog(null)}
          submit={(reason) => actions.voidSelected(ids, reason)}
        />
      ) : null}
    </>
  );
}
