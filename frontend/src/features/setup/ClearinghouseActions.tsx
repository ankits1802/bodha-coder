"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { useAction } from "@/hooks/useAction";
import { removeClearinghouse, testClearinghouse } from "@/lib/api/clearinghouse";
import type { ClearinghouseConnection, ClearinghouseView } from "@/lib/api/types";
import { CLEARINGHOUSE_TEXT } from "./strings";

interface ClearinghouseActionsProps {
  connection: ClearinghouseConnection;
  onRemoved: (view: ClearinghouseView) => void;
}

export function ClearinghouseActions({ connection, onRemoved }: ClearinghouseActionsProps) {
  const test = useAction(testClearinghouse);
  const remove = useAction(removeClearinghouse);
  const [tested, setTested] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const words = CLEARINGHOUSE_TEXT;

  async function runTest(): Promise<void> {
    setTested(false);
    const outcome = await test.run();
    if (outcome.ok) setTested(outcome.value.ok);
  }

  async function confirmRemove(): Promise<void> {
    const outcome = await remove.run();
    if (!outcome.ok) return;
    setConfirming(false);
    onRemoved(outcome.value);
  }

  return (
    <>
      {tested ? (
        <span role="status" className="text-subhead text-secondary">
          {words.tested}
        </span>
      ) : null}
      {test.error ? (
        <span role="alert" className="text-footnote text-bad-text">
          {test.error}
        </span>
      ) : null}
      <Button
        variant="danger"
        onClick={() => {
          remove.clearError();
          setConfirming(true);
        }}
      >
        {words.remove}
      </Button>
      {connection.transport === "sftp" ? (
        <Button pending={test.pending} onClick={() => void runTest()}>
          {words.test}
        </Button>
      ) : null}
      <ConfirmDialog
        open={confirming}
        title={words.confirm.title}
        confirmLabel={words.confirm.action}
        cancelLabel={words.confirm.cancel}
        destructive
        pending={remove.pending}
        error={remove.error}
        onConfirm={() => void confirmRemove()}
        onClose={() => setConfirming(false)}
      />
    </>
  );
}
