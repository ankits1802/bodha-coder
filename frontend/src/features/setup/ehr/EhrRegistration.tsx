"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Select } from "@/components/ui/Select";
import { useAction } from "@/hooks/useAction";
import { createEhrKey } from "@/lib/api/ehrConnection";
import type { EhrConnection, EhrKeyAlgorithm, EhrRegistration as Registration } from "@/lib/api/types";
import { CopyRow } from "./CopyRow";
import { EHR_TEXT } from "./strings";

interface EhrRegistrationProps {
  view: EhrConnection;
  onChange: (view: EhrConnection) => void;
}

const words = EHR_TEXT;
const ALGORITHMS: readonly EhrKeyAlgorithm[] = ["RS384", "ES384"];

function RegistrationFacts({ registration }: { registration: Registration }) {
  const facts = [
    [words.algorithm, registration.algorithm],
    [words.grantType, registration.grant_type],
    [words.authMethod, registration.auth_method],
  ] as const;
  return (
    <dl className="m-0 grid grid-cols-[minmax(0,12rem)_minmax(0,1fr)] gap-x-4 gap-y-1.5 text-body">
      {facts.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="text-secondary">{label}</dt>
          <dd className="m-0 break-all text-label">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function EhrRegistration({ view, onChange }: EhrRegistrationProps) {
  const [algorithm, setAlgorithm] = useState<EhrKeyAlgorithm>(view.registration?.algorithm ?? "RS384");
  const [confirming, setConfirming] = useState(false);
  const create = useAction(createEhrKey);
  const registration = view.registration;

  async function makeKey(): Promise<void> {
    const outcome = await create.run(algorithm);
    if (!outcome.ok) return;
    setConfirming(false);
    onChange(outcome.value);
  }

  return (
    <div className="flex flex-col gap-4 border-t border-hairline px-4 py-4">
      <span className="text-subhead font-medium text-label">{words.registration}</span>
      {registration ? (
        <>
          <CopyRow label={words.jwksUrl} value={registration.jwks_url} />
          <CopyRow label={words.keyId} value={registration.key_id} />
          <RegistrationFacts registration={registration} />
        </>
      ) : null}
      <div className="flex flex-wrap items-end gap-3">
        <Field label={words.algorithm} className="min-w-40">
          {(control) => (
            <Select
              {...control}
              value={algorithm}
              options={ALGORITHMS.map((value) => ({ value, label: words.algorithms[value] }))}
              onChange={setAlgorithm}
              className="max-w-40"
            />
          )}
        </Field>
        {registration ? (
          <Button size="sm" onClick={() => setConfirming(true)}>
            {words.newKey}
          </Button>
        ) : (
          <Button variant="primary" pending={create.pending} onClick={() => void makeKey()}>
            {words.createKey}
          </Button>
        )}
      </div>
      {create.error && !confirming ? <InlineAlert tone="bad">{create.error}</InlineAlert> : null}
      <ConfirmDialog
        open={confirming}
        title={words.newKeyTitle}
        confirmLabel={words.replace}
        cancelLabel={words.cancel}
        destructive
        pending={create.pending}
        error={create.error}
        onConfirm={() => void makeKey()}
        onClose={() => setConfirming(false)}
      />
    </div>
  );
}
