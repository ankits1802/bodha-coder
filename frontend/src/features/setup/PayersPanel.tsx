"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { useAction } from "@/hooks/useAction";
import { removePayer } from "@/lib/api/practice";
import type { Payer } from "@/lib/api/types";
import { PayerDialog } from "./PayerDialog";
import { PayersTable } from "./PayersTable";
import { PAYER_TEXT } from "./strings";
import { useArrival } from "./useArrival";

interface PayersPanelProps {
  payers: Payer[];
  addOnArrival: boolean;
  onArrived: () => void;
  onChanged: () => void;
}

export function PayersPanel({ payers, addOnArrival, onArrived, onChanged }: PayersPanelProps) {
  const [editing, setEditing] = useState<Payer | "new" | null>(() => (addOnArrival ? "new" : null));
  useArrival(addOnArrival, onArrived);
  const [removing, setRemoving] = useState<Payer | null>(null);
  const remove = useAction(removePayer);

  async function confirmRemove(): Promise<void> {
    if (!removing) return;
    const outcome = await remove.run(removing.id);
    if (!outcome.ok) return;
    setRemoving(null);
    onChanged();
  }

  return (
    <Panel aria-label={PAYER_TEXT.title}>
      <PanelHeader
        title={PAYER_TEXT.title}
        actions={
          <Button size="sm" onClick={() => setEditing("new")}>
            {PAYER_TEXT.add}
          </Button>
        }
      />
      {payers.length === 0 ? (
        <EmptyState title={PAYER_TEXT.empty} />
      ) : (
        <PayersTable
          payers={payers}
          onEdit={setEditing}
          onRemove={(payer) => {
            remove.clearError();
            setRemoving(payer);
          }}
        />
      )}
      {editing !== null ? (
        <PayerDialog
          payer={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            onChanged();
          }}
        />
      ) : null}
      <ConfirmDialog
        open={removing !== null}
        title={removing ? PAYER_TEXT.confirm.title(removing.name) : ""}
        confirmLabel={PAYER_TEXT.confirm.action}
        cancelLabel={PAYER_TEXT.confirm.cancel}
        destructive
        pending={remove.pending}
        error={remove.error}
        onConfirm={() => void confirmRemove()}
        onClose={() => setRemoving(null)}
      />
    </Panel>
  );
}
