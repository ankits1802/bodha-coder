"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { chooseJoin } from "@/lib/api/signupJoin";
import type { JoinPage, JoinResult } from "@/lib/api/types";
import { SIGN_UP_TEXT } from "./strings";

const words = SIGN_UP_TEXT.join;

function Done({ page, result }: { page: JoinPage; result: JoinResult }) {
  if (result === "requested" && page.join) return <InlineAlert tone="ok">{words.requested(page.join.practice_name)}</InlineAlert>;
  return <InlineAlert tone="ok">{words.checkEmail}</InlineAlert>;
}

export function JoinChoices({ token, page }: { token: string; page: JoinPage }) {
  const choose = useAction(chooseJoin);
  const [result, setResult] = useState<JoinResult | null>(null);
  const offer = page.join;

  async function pick(join: boolean): Promise<void> {
    const outcome = await choose.run({ token, join });
    if (outcome.ok) setResult(outcome.value.outcome);
  }

  if (result) return <Done page={page} result={result} />;
  return (
    <div className="flex flex-col gap-4">
      <h2 className="m-0 text-center font-sans text-headline font-semibold tracking-snug">
        {offer ? words.title(offer.practice_name) : SIGN_UP_TEXT.completeTitle}
      </h2>
      <div className="flex flex-col gap-0.5">
        <span className="text-subhead font-medium text-label">{SIGN_UP_TEXT.email}</span>
        <span className="text-body text-secondary">{page.email}</span>
      </div>
      {choose.error ? <InlineAlert tone="bad">{choose.error}</InlineAlert> : null}
      {offer ? (
        <Button variant="primary" size="lg" className="w-full" pending={choose.pending} onClick={() => void pick(true)}>
          {offer.mode === "auto" ? words.join(offer.practice_name) : words.ask(offer.practice_name)}
        </Button>
      ) : null}
      <Button
        variant={offer ? "secondary" : "primary"}
        size="lg"
        className="w-full"
        disabled={choose.pending}
        onClick={() => void pick(false)}
      >
        {words.startOwn(page.own_practice_name)}
      </Button>
    </div>
  );
}
