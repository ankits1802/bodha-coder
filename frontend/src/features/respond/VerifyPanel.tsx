"use client";

import { useState, type FormEvent } from "react";
import { CodeInput } from "@/components/shared/CodeInput";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { sendProviderCode, verifyProviderCode } from "@/lib/api/respond";
import { isSixDigitCode } from "@/lib/validation";
import { RESPOND_TEXT } from "./strings";

interface VerifyPanelProps {
  token: string;
  expired: boolean;
  onVerified: (providerToken: string) => void;
}

export function VerifyPanel({ token, expired, onVerified }: VerifyPanelProps) {
  const send = useAction(sendProviderCode);
  const verify = useAction(verifyProviderCode);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [incomplete, setIncomplete] = useState(false);

  async function requestCode(): Promise<void> {
    verify.clearError();
    const outcome = await send.run(token);
    if (!outcome.ok) return;
    setSentTo(outcome.value.sent_to);
    setCode("");
  }

  async function check(value: string): Promise<void> {
    const ready = isSixDigitCode(value);
    setIncomplete(!ready);
    if (!ready) return;
    const outcome = await verify.run(token, value);
    if (outcome.ok) onVerified(outcome.value.provider_token);
  }

  function typed(value: string): void {
    setCode(value);
    if (isSixDigitCode(value) && !verify.pending) void check(value);
  }

  return (
    <div className="mx-auto flex w-full max-w-90 flex-col gap-5.5 py-16">
      <h1 className="m-0 text-center text-title2 font-bold tracking-headline">{RESPOND_TEXT.verifyTitle}</h1>
      {expired && sentTo === null ? <InlineAlert tone="warn">{RESPOND_TEXT.expired}</InlineAlert> : null}
      {send.error ? <InlineAlert tone="bad">{send.error}</InlineAlert> : null}
      {sentTo === null ? (
        <Button variant="primary" size="lg" pending={send.pending} onClick={() => void requestCode()} className="w-full">
          {RESPOND_TEXT.sendCode}
        </Button>
      ) : (
        <form
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            void check(code);
          }}
          noValidate
          className="flex flex-col gap-5.5"
        >
          <p className="m-0 text-center text-body text-secondary">{RESPOND_TEXT.codeSentTo(sentTo)}</p>
          <CodeInput
            value={code}
            onChange={typed}
            label={RESPOND_TEXT.codeLabel}
            digitLabel={RESPOND_TEXT.digitLabel}
            disabled={verify.pending}
            autoFocus
          />
          {incomplete ? <InlineAlert tone="bad">{RESPOND_TEXT.incompleteCode}</InlineAlert> : null}
          {verify.error && !incomplete ? <InlineAlert tone="bad">{verify.error}</InlineAlert> : null}
          <Button type="submit" variant="primary" size="lg" pending={verify.pending} className="w-full">
            {RESPOND_TEXT.verify}
          </Button>
          <Button variant="plain" size="sm" pending={send.pending} onClick={() => void requestCode()} className="self-center">
            {RESPOND_TEXT.sendNewCode}
          </Button>
        </form>
      )}
    </div>
  );
}
