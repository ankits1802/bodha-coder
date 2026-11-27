"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Input } from "@/components/ui/Input";
import { useAction } from "@/hooks/useAction";
import { isJoinOutcome, joinWithIdentity } from "@/lib/api/signupJoin";
import type { JoinOffer, LoginResult, PendingIdentity } from "@/lib/api/types";
import { SIGN_UP_TEXT } from "./strings";

const words = SIGN_UP_TEXT.join;

interface IdentityJoinProps {
  identity: PendingIdentity;
  offer: JoinOffer;
  onSignedIn: (result: LoginResult) => void;
  onOwn: () => void;
}

export function IdentityJoin({ identity, offer, onSignedIn, onOwn }: IdentityJoinProps) {
  const [name, setName] = useState(identity.name);
  const [missing, setMissing] = useState(false);
  const [requested, setRequested] = useState(false);
  const join = useAction(joinWithIdentity);
  const named = identity.has_account ? identity.name || identity.email : name.trim();

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!named) {
      setMissing(true);
      return;
    }
    const outcome = await join.run({ name: named });
    if (!outcome.ok) return;
    if (isJoinOutcome(outcome.value)) setRequested(true);
    else onSignedIn(outcome.value);
  }

  if (requested) return <InlineAlert tone="ok">{words.requested(offer.practice_name)}</InlineAlert>;
  return (
    <form onSubmit={(event) => void submit(event)} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-0.5">
        <span className="text-subhead font-medium text-label">{SIGN_UP_TEXT.signedInAs}</span>
        <span className="text-body text-secondary">{identity.email}</span>
      </div>
      {identity.has_account ? null : (
        <Field label={SIGN_UP_TEXT.name} error={missing ? words.nameRequired : null}>
          {(control) => (
            <Input {...control} value={name} autoComplete="name" onChange={(event) => setName(event.target.value)} />
          )}
        </Field>
      )}
      {join.error ? <InlineAlert tone="bad">{join.error}</InlineAlert> : null}
      <Button type="submit" variant="primary" size="lg" pending={join.pending} className="w-full">
        {offer.mode === "auto" ? words.join(offer.practice_name) : words.ask(offer.practice_name)}
      </Button>
      <Button variant="secondary" size="lg" className="w-full" onClick={onOwn}>
        {words.own}
      </Button>
    </form>
  );
}
