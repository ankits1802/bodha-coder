"use client";

import { useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { useAction } from "@/hooks/useAction";
import { saveClearinghouse } from "@/lib/api/clearinghouse";
import type { ClearinghouseView } from "@/lib/api/types";
import { ClearinghouseActions } from "./ClearinghouseActions";
import {
  connectionDraftFrom,
  connectionInputFrom,
  keepsSavedSecret,
  validateConnection,
  type ConnectionDraft,
  type ConnectionErrors,
  type DraftChange,
} from "./connectionModel";
import { ConnectionIdentityFields } from "./ConnectionIdentityFields";
import { HostKeyField } from "./HostKeyField";
import { SftpFields } from "./SftpFields";
import { CLEARINGHOUSE_TEXT } from "./strings";

interface ClearinghouseFormProps {
  view: ClearinghouseView;
  onSaved: (view: ClearinghouseView) => void;
  onRemoved: (view: ClearinghouseView) => void;
}

export function ClearinghouseForm({ view, onSaved, onRemoved }: ClearinghouseFormProps) {
  const connection = view.connection;
  const [draft, setDraft] = useState<ConnectionDraft>(() => connectionDraftFrom(connection));
  const [errors, setErrors] = useState<ConnectionErrors>({});
  const save = useAction(saveClearinghouse);
  const formId = useId();
  const words = CLEARINGHOUSE_TEXT;
  const sftp = draft.transport === "sftp";
  const change: DraftChange = (part) => setDraft((current) => ({ ...current, ...part }));

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const found = validateConnection(draft, connection);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    const outcome = await save.run(connectionInputFrom(draft));
    if (outcome.ok) onSaved(outcome.value);
  }

  return (
    <Panel aria-labelledby={`${formId}-title`}>
      <PanelHeader title={<span id={`${formId}-title`}>{words.title}</span>} />
      <form id={formId} noValidate onSubmit={submit} className="grid gap-4 px-4 pb-4 sm:grid-cols-2">
        {sftp && !view.encryption_ready ? (
          <div className="sm:col-span-2">
            <InlineAlert tone="warn">{words.noKey}</InlineAlert>
          </div>
        ) : null}
        <ConnectionIdentityFields draft={draft} errors={errors} onChange={change} />
        {sftp ? (
          <>
            <SftpFields draft={draft} errors={errors} secretSaved={keepsSavedSecret(draft, connection)} onChange={change} />
            <HostKeyField draft={draft} error={errors.host_key_sha256} onChange={change} />
          </>
        ) : null}
        <div className="flex flex-wrap items-center justify-end gap-3 sm:col-span-2">
          {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
          {connection ? <ClearinghouseActions connection={connection} onRemoved={onRemoved} /> : null}
          <Button type="submit" variant="primary" pending={save.pending}>
            {words.save}
          </Button>
        </div>
      </form>
    </Panel>
  );
}
