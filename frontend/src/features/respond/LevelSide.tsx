"use client";

import { useState, type ReactNode } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { useAction } from "@/hooks/useAction";
import { answerLevelChange } from "@/lib/api/respond";
import type { LevelChangeBody, LevelChangeResult, LevelChangeView, ProviderRequest } from "@/lib/api/types";
import { LevelChangeForm } from "./LevelChangeForm";
import { watchExpiry } from "./providerSession";
import { RESPOND_TEXT } from "./strings";

interface LevelSideProps {
  request: ProviderRequest;
  change: LevelChangeView;
  providerToken: string;
  next: ReactNode;
  onExpired: () => void;
}

function Answered({ result, next }: { result: LevelChangeResult; next: ReactNode }) {
  return (
    <Panel role="status" className="flex flex-col items-center gap-3 px-7 py-9 text-center">
      <h2 className="m-0 font-sans text-title3 font-semibold tracking-headline">
        {result.answer === "confirm" ? RESPOND_TEXT.levelConfirmed : RESPOND_TEXT.levelDisagreed}
      </h2>
      {next}
    </Panel>
  );
}

export function LevelSide({ request, change, providerToken, next, onExpired }: LevelSideProps) {
  const send = useAction((body: LevelChangeBody) => watchExpiry(answerLevelChange(providerToken, body), onExpired));
  const [result, setResult] = useState<LevelChangeResult | null>(null);

  async function submit(body: LevelChangeBody): Promise<void> {
    const outcome = await send.run(body);
    if (outcome.ok) setResult(outcome.value);
  }

  if (result) return <Answered result={result} next={next} />;
  if (request.status !== "sent") {
    return (
      <Panel>
        <EmptyState title={RESPOND_TEXT.closed} />
      </Panel>
    );
  }
  return (
    <LevelChangeForm change={change} attestation={request.attestation} pending={send.pending} error={send.error} onSend={(body) => void submit(body)} />
  );
}
