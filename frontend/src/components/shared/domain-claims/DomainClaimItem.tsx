"use client";

import { useState } from "react";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { StatusDot } from "@/components/ui/StatusDot";
import { useAction } from "@/hooks/useAction";
import { releaseDomain, type DomainScope } from "@/lib/api/domains";
import type { DomainClaim } from "@/lib/api/types";
import { JoinSetting } from "./JoinSetting";
import { DOMAIN_TEXT } from "./strings";
import { VerifyControls } from "./VerifyControls";

interface DomainClaimItemProps {
  scope: DomainScope;
  claim: DomainClaim;
  showPractice: boolean;
  onChanged: () => void;
}

const words = DOMAIN_TEXT;

export function DomainClaimItem({ scope, claim, showPractice, onChanged }: DomainClaimItemProps) {
  const [releasing, setReleasing] = useState(false);
  const release = useAction(releaseDomain);

  async function confirmRelease(): Promise<void> {
    if (!(await release.run(scope, claim.id)).ok) return;
    setReleasing(false);
    onChanged();
  }

  return (
    <li className="flex flex-col gap-3 border-t border-hairline px-4 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-wrap items-center gap-3">
          <span className="text-body font-medium break-all text-label">{claim.domain}</span>
          {showPractice ? <span className="text-subhead text-secondary">{claim.practice_name}</span> : null}
          <StatusDot tone={claim.verified ? "ok" : "warn"}>{claim.verified ? words.verified : words.unverified}</StatusDot>
        </div>
        <Button variant="plain" size="sm" aria-label={words.releaseFor(claim.domain)} onClick={() => setReleasing(true)}>
          {words.release}
        </Button>
      </div>
      {claim.verified ? (
        <JoinSetting scope={scope} claim={claim} onChanged={onChanged} />
      ) : (
        <VerifyControls scope={scope} claim={claim} onChanged={onChanged} />
      )}
      <ConfirmDialog
        open={releasing}
        title={words.releaseTitle(claim.domain)}
        confirmLabel={words.release}
        cancelLabel={words.cancel}
        destructive
        pending={release.pending}
        error={release.error}
        onConfirm={() => void confirmRelease()}
        onClose={() => setReleasing(false)}
      />
    </li>
  );
}
