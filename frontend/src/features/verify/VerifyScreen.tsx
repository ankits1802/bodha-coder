"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { verifySeal } from "@/lib/api/signatures";
import { normalCode } from "./fingerprint";
import { VERIFY_TEXT } from "./strings";
import { VerifyResult } from "./VerifyResult";

const REMOTE_TEXT = { loading: VERIFY_TEXT.checking, empty: "", retry: VERIFY_TEXT.verify };

export function VerifyScreen() {
  const router = useRouter();
  const params = useSearchParams();
  const given = params.get("code") ?? "";
  const code = normalCode(given);
  const [typed, setTyped] = useState(given);
  const [touched, setTouched] = useState(false);
  const remote = useRemote(code ? `verify:${code}` : null, () => verifySeal(code ?? ""));
  const normal = normalCode(typed);

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setTouched(true);
    if (!normal) return;
    if (normal === code) remote.reload();
    else router.replace(`/verify?code=${encodeURIComponent(normal)}`);
  }

  return (
    <main className="min-h-screen bg-page px-4 py-12">
      <div className="mx-auto flex w-full max-w-150 flex-col gap-6">
        <PageHeader title={VERIFY_TEXT.title} />
        <Panel className="px-5 py-4.5">
          <form className="flex flex-wrap items-start gap-3" noValidate onSubmit={submit}>
            <Field label={VERIFY_TEXT.code} error={touched && !normal ? VERIFY_TEXT.incomplete : null} className="min-w-0 flex-1">
              {(control) => (
                <Input
                  {...control}
                  value={typed}
                  autoComplete="off"
                  spellCheck={false}
                  onChange={(event) => setTyped(event.target.value)}
                  onBlur={() => setTouched(true)}
                />
              )}
            </Field>
            <Button type="submit" variant="primary" className="mt-6.5">
              {VERIFY_TEXT.verify}
            </Button>
          </form>
        </Panel>
        {code ? (
          <RemoteView state={remote.state} text={REMOTE_TEXT} onRetry={remote.reload}>
            {(result) => <VerifyResult result={result} />}
          </RemoteView>
        ) : null}
      </div>
    </main>
  );
}
