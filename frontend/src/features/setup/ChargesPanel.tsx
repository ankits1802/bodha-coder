"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getCharges, importCharges, removeCharge } from "@/lib/api/clearinghouse";
import type { Charge, ChargeList } from "@/lib/api/types";
import { ChargeDialog } from "./ChargeDialog";
import { ChargesTable } from "./ChargesTable";
import { ImportDialog } from "./ImportDialog";
import { CHARGE_TEXT } from "./strings";

const REMOTE_TEXT = { loading: CHARGE_TEXT.loading, empty: CHARGE_TEXT.empty, retry: CHARGE_TEXT.retry };

function importChargeRows(csv: string): Promise<number> {
  return importCharges(csv).then((list) => list.items.length);
}

export function ChargesPanel() {
  const charges = useRemote("setup-charges", getCharges);
  const [editing, setEditing] = useState<Charge | "new" | null>(null);
  const [removing, setRemoving] = useState<Charge | null>(null);
  const [importing, setImporting] = useState(false);
  const [imported, setImported] = useState<number | null>(null);
  const remove = useAction(removeCharge);

  function saved(list: ChargeList): void {
    setEditing(null);
    charges.replace(list);
  }

  async function confirmRemove(): Promise<void> {
    if (!removing) return;
    const outcome = await remove.run(removing.code);
    if (!outcome.ok) return;
    setRemoving(null);
    charges.replace(outcome.value);
  }

  return (
    <Panel aria-label={CHARGE_TEXT.title}>
      <PanelHeader
        title={CHARGE_TEXT.title}
        actions={
          <>
            <Button size="sm" onClick={() => setImporting(true)}>
              {CHARGE_TEXT.import}
            </Button>
            <Button size="sm" onClick={() => setEditing("new")}>
              {CHARGE_TEXT.add}
            </Button>
          </>
        }
      />
      {imported !== null ? (
        <div className="px-4 pb-3">
          <InlineAlert tone="ok">{CHARGE_TEXT.importDialog.imported(imported)}</InlineAlert>
        </div>
      ) : null}
      <RemoteView state={charges.state} text={REMOTE_TEXT} isEmpty={(data) => data.items.length === 0} onRetry={charges.reload}>
        {(data) => (
          <ChargesTable
            charges={data.items}
            onEdit={setEditing}
            onRemove={(charge) => {
              remove.clearError();
              setRemoving(charge);
            }}
          />
        )}
      </RemoteView>
      {editing !== null ? <ChargeDialog charge={editing === "new" ? null : editing} onClose={() => setEditing(null)} onSaved={saved} /> : null}
      {importing ? (
        <ImportDialog
          words={CHARGE_TEXT.importDialog}
          run={importChargeRows}
          onClose={() => setImporting(false)}
          onImported={(count) => {
            setImporting(false);
            setImported(count);
            charges.reload();
          }}
        />
      ) : null}
      <ConfirmDialog
        open={removing !== null}
        title={removing ? CHARGE_TEXT.confirm.title(removing.code) : ""}
        confirmLabel={CHARGE_TEXT.confirm.action}
        cancelLabel={CHARGE_TEXT.confirm.cancel}
        destructive
        pending={remove.pending}
        error={remove.error}
        onConfirm={() => void confirmRemove()}
        onClose={() => setRemoving(null)}
      />
    </Panel>
  );
}
