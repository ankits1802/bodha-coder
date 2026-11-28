import { useId } from "react";
import { buttonClasses } from "@/components/ui/buttonStyles";
import type { SsoConnection } from "@/lib/api/types";
import { SSO_TEXT } from "./strings";

const VALUE = "rounded-nav bg-control px-2 py-1 font-mono text-footnote break-all text-label select-all";

function CopyRow({ label, value }: { label: string; value: string }) {
  const labelId = useId();
  return (
    <div className="flex flex-col gap-1">
      <span id={labelId} className="text-subhead font-medium text-label">
        {label}
      </span>
      <code aria-labelledby={labelId} className={VALUE}>
        {value}
      </code>
    </div>
  );
}

export function ServiceProviderDetails({ connection }: { connection: SsoConnection }) {
  const provider = connection.service_provider;
  return (
    <section aria-label={SSO_TEXT.serviceProvider} className="flex flex-col gap-3 border-t border-hairline px-4 py-4">
      <h3 className="m-0 text-body font-semibold">{SSO_TEXT.serviceProvider}</h3>
      <CopyRow label={SSO_TEXT.entityId} value={provider.entity_id} />
      <CopyRow label={SSO_TEXT.acsUrl} value={provider.acs_url} />
      <CopyRow label={SSO_TEXT.nameIdFormat} value={SSO_TEXT.emailFormat} />
      <a href={provider.metadata_url} download className={buttonClasses("secondary", "sm", "self-start")}>
        {SSO_TEXT.downloadMetadata}
      </a>
    </section>
  );
}
