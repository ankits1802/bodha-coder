"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import type { DomainScope } from "@/lib/api/domains";
import { removeSso, saveSso } from "@/lib/api/sso";
import type { SsoConnection, SsoSettings } from "@/lib/api/types";
import { DomainsSection } from "./DomainsSection";
import { IdentityProviderSection } from "./IdentityProviderSection";
import { PeopleSection } from "./PeopleSection";
import { RequiredSection } from "./RequiredSection";
import { ServiceProviderDetails } from "./ServiceProviderDetails";
import { draftFrom, requestFrom, withImported, withoutCertificate, type SsoDraft } from "./ssoDraft";
import { SSO_TEXT } from "./strings";
import { TestSection } from "./TestSection";

interface SsoFormProps {
  scope: DomainScope;
  settings: SsoSettings;
  connection: SsoConnection;
  onChanged: (settings: SsoSettings) => void;
}

export function SsoForm({ scope, settings, connection, onChanged }: SsoFormProps) {
  const [draft, setDraft] = useState<SsoDraft>(() => draftFrom(connection.current));
  const [saved, setSaved] = useState(false);
  const [removing, setRemoving] = useState(false);
  const save = useAction(saveSso);
  const remove = useAction(removeSso);
  const body = requestFrom(draft);

  function change(next: Partial<SsoDraft>): void {
    setSaved(false);
    setDraft((current) => ({ ...current, ...next }));
  }

  async function submit(): Promise<void> {
    if (!body) return;
    const outcome = await save.run(scope, body);
    if (!outcome.ok) return;
    setSaved(true);
    onChanged(outcome.value);
  }

  async function confirmRemove(): Promise<void> {
    const outcome = await remove.run(scope);
    if (!outcome.ok) return;
    setRemoving(false);
    onChanged(outcome.value);
  }

  return (
    <>
      <ServiceProviderDetails connection={connection} />
      <IdentityProviderSection
        scope={scope}
        provider={draft.provider}
        onImported={(provider) => change(withImported(draft, provider))}
        onRemoveCertificate={(value) => change(withoutCertificate(draft, value))}
      />
      <DomainsSection
        domains={settings.domains}
        chosen={draft.claimIds}
        showPractice={scope.kind === "organization"}
        onChange={(claimIds) => change({ claimIds })}
      />
      <PeopleSection draft={draft} onChange={change} />
      <RequiredSection draft={draft} admins={settings.admins} onChange={change} />
      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-hairline px-4 py-3">
        {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
        {connection.current ? <span className="text-subhead text-secondary">{SSO_TEXT.version(connection.current.version)}</span> : null}
        {saved ? (
          <span role="status" className="text-subhead text-secondary">
            {SSO_TEXT.saved}
          </span>
        ) : null}
        <Button variant="plain" onClick={() => setRemoving(true)}>
          {SSO_TEXT.removeAll}
        </Button>
        <Button pending={save.pending} disabled={!body} onClick={() => void submit()}>
          {SSO_TEXT.save}
        </Button>
      </div>
      <TestSection scope={scope} ready={connection.current !== null} />
      <ConfirmDialog
        open={removing}
        title={SSO_TEXT.removeTitle}
        confirmLabel={SSO_TEXT.removeAll}
        cancelLabel={SSO_TEXT.cancel}
        destructive
        pending={remove.pending}
        error={remove.error}
        onConfirm={() => void confirmRemove()}
        onClose={() => setRemoving(false)}
      />
    </>
  );
}
