"use client";

import { useState } from "react";
import { AuthFrame } from "@/components/shared/AuthFrame";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/ErrorState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { useAction } from "@/hooks/useAction";
import { useFragmentToken } from "@/hooks/useFragmentToken";
import { verifyDomainLink } from "@/lib/api/domainVerification";
import type { VerifiedDomain } from "@/lib/api/types";
import { VERIFY_DOMAIN_TEXT } from "./strings";

const words = VERIFY_DOMAIN_TEXT;

function Confirm({ token }: { token: string }) {
  const confirm = useAction(verifyDomainLink);
  const [verified, setVerified] = useState<VerifiedDomain | null>(null);

  async function run(): Promise<void> {
    const outcome = await confirm.run(token);
    if (outcome.ok) setVerified(outcome.value);
  }

  if (verified) return <InlineAlert tone="ok">{words.verified(verified.domain, verified.practice_name)}</InlineAlert>;
  return (
    <div className="flex flex-col gap-4">
      <h2 className="m-0 text-center font-sans text-headline font-semibold tracking-snug">{words.title}</h2>
      {confirm.error ? <InlineAlert tone="bad">{confirm.error}</InlineAlert> : null}
      <Button variant="primary" size="lg" className="w-full" pending={confirm.pending} onClick={() => void run()}>
        {words.confirm}
      </Button>
    </div>
  );
}

export function VerifyDomainScreen() {
  const token = useFragmentToken();
  return (
    <AuthFrame>
      {token === undefined ? <LoadingState label={words.loading} /> : null}
      {token === null ? <ErrorState message={words.invalidLink} /> : null}
      {token ? <Confirm token={token} /> : null}
    </AuthFrame>
  );
}
