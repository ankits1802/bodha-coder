"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { domainScopeKey, getDomainClaims, type DomainScope } from "@/lib/api/domains";
import { ClaimForm } from "./ClaimForm";
import { DomainClaimItem } from "./DomainClaimItem";
import type { PracticeOption } from "./domainModel";
import { DOMAIN_TEXT } from "./strings";

interface DomainClaimsProps {
  scope: DomainScope;
  practices?: readonly PracticeOption[];
}

const words = DOMAIN_TEXT;
const TEXT = { loading: words.loading, empty: words.loading, retry: words.retry };

export function DomainClaims({ scope, practices }: DomainClaimsProps) {
  const remote = useRemote(domainScopeKey(scope), () => getDomainClaims(scope));
  return (
    <Panel aria-label={words.title}>
      <PanelHeader title={words.title} />
      <ClaimForm scope={scope} practices={practices} onClaimed={remote.reload} />
      <RemoteView state={remote.state} text={TEXT} onRetry={remote.reload}>
        {(claims) =>
          claims.length > 0 ? (
            <ul aria-label={words.listLabel} className="m-0 list-none p-0">
              {claims.map((claim) => (
                <DomainClaimItem
                  key={claim.id}
                  scope={scope}
                  claim={claim}
                  showPractice={practices !== undefined}
                  onChanged={remote.reload}
                />
              ))}
            </ul>
          ) : null
        }
      </RemoteView>
    </Panel>
  );
}
