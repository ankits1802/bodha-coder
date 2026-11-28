import type { SsoDomain } from "@/lib/api/types";
import { toggled } from "./ssoDraft";
import { SSO_TEXT } from "./strings";
import { ToggleRow } from "./ToggleRow";

interface DomainsSectionProps {
  domains: readonly SsoDomain[];
  chosen: readonly string[];
  showPractice: boolean;
  onChange: (claimIds: string[]) => void;
}

export function DomainsSection({ domains, chosen, showPractice, onChange }: DomainsSectionProps) {
  return (
    <section aria-label={SSO_TEXT.domains} className="flex flex-col gap-1 border-t border-hairline px-4 py-4">
      <h3 className="m-0 text-body font-semibold">{SSO_TEXT.domains}</h3>
      {domains.length === 0 ? <p className="m-0 text-body text-secondary">{SSO_TEXT.noDomains}</p> : null}
      {domains.map((domain) => (
        <ToggleRow
          key={domain.claim_id}
          label={domain.domain}
          toggleLabel={SSO_TEXT.domainFor(domain.domain)}
          checked={chosen.includes(domain.claim_id)}
          detail={showPractice ? <span className="text-subhead text-secondary">{domain.practice_name}</span> : null}
          onChange={(on) => onChange(toggled(chosen, domain.claim_id, on))}
        />
      ))}
    </section>
  );
}
