"use client";

import { useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import type { DomainScope } from "@/lib/api/domains";
import { readSsoMetadata } from "@/lib/api/sso";
import type { SsoIdentityProvider } from "@/lib/api/types";
import { CertificateList } from "./CertificateList";
import { SSO_TEXT } from "./strings";

interface IdentityProviderSectionProps {
  scope: DomainScope;
  provider: SsoIdentityProvider | null;
  onImported: (provider: SsoIdentityProvider) => void;
  onRemoveCertificate: (value: string) => void;
}

export function IdentityProviderSection({ scope, provider, onImported, onRemoveCertificate }: IdentityProviderSectionProps) {
  const [url, setUrl] = useState("");
  const read = useAction(readSsoMetadata);

  async function readFile(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const outcome = await read.run(scope, { xml: await file.text() });
    if (outcome.ok) onImported(outcome.value);
  }

  async function fetchUrl(): Promise<void> {
    const outcome = await read.run(scope, { url: url.trim() });
    if (outcome.ok) onImported(outcome.value);
  }

  return (
    <section aria-label={SSO_TEXT.identityProvider} className="flex flex-col gap-4 border-t border-hairline px-4 py-4">
      <h3 className="m-0 text-body font-semibold">{SSO_TEXT.identityProvider}</h3>
      <Field label={SSO_TEXT.metadataFile}>
        {(control) => (
          <input {...control} type="file" accept=".xml,application/xml,text/xml" onChange={(event) => void readFile(event)} className="text-body" />
        )}
      </Field>
      <div className="flex flex-wrap items-end gap-3">
        <Field label={SSO_TEXT.metadataUrl} className="min-w-64 flex-1">
          {(control) => (
            <Input {...control} type="url" value={url} autoComplete="off" spellCheck={false} onChange={(event) => setUrl(event.target.value)} />
          )}
        </Field>
        <Button pending={read.pending} disabled={url.trim() === ""} onClick={() => void fetchUrl()}>
          {SSO_TEXT.fetch}
        </Button>
      </div>
      {read.error ? <InlineAlert tone="bad">{read.error}</InlineAlert> : null}
      {provider ? (
        <dl className="m-0 grid grid-cols-1 gap-2 text-body sm:grid-cols-[max-content_1fr] sm:gap-x-4">
          <dt className="text-secondary">{SSO_TEXT.entityId}</dt>
          <dd className="m-0 break-all">{provider.entity_id}</dd>
          <dt className="text-secondary">{SSO_TEXT.ssoUrl}</dt>
          <dd className="m-0 break-all">{provider.sso_url}</dd>
        </dl>
      ) : null}
      {provider ? <CertificateList certificates={provider.certificates} onRemove={onRemoveCertificate} /> : null}
    </section>
  );
}
