"use client";

import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { useAction } from "@/hooks/useAction";
import { useFragmentToken } from "@/hooks/useFragmentToken";
import { useRemote } from "@/hooks/useRemote";
import type { DomainScope } from "@/lib/api/domains";
import { readSsoTestResult, SSO_TEST_FRAGMENT, ssoScopeKey, startSsoTest } from "@/lib/api/sso";
import { openPage } from "@/lib/openPage";
import { SSO_TEXT } from "./strings";
import { TestResult } from "./TestResult";

interface TestSectionProps {
  scope: DomainScope;
  ready: boolean;
}

export function testTokenOf(fragment: string | null | undefined): string | null {
  return fragment ? new URLSearchParams(fragment).get(SSO_TEST_FRAGMENT) : null;
}

export function TestSection({ scope, ready }: TestSectionProps) {
  const token = testTokenOf(useFragmentToken());
  const result = useRemote(token ? `${ssoScopeKey(scope)}:test:${token}` : null, () => readSsoTestResult(scope, token ?? ""));
  const start = useAction(startSsoTest);

  async function run(): Promise<void> {
    const outcome = await start.run(scope);
    if (outcome.ok) openPage(outcome.value.url);
  }

  return (
    <section aria-label={SSO_TEXT.test} className="flex flex-col gap-3 border-t border-hairline px-4 py-4">
      <Button className="self-start" disabled={!ready} pending={start.pending} onClick={() => void run()}>
        {SSO_TEXT.test}
      </Button>
      {start.error ? <InlineAlert tone="bad">{start.error}</InlineAlert> : null}
      {result.state.status === "success" ? <TestResult result={result.state.data} /> : null}
      {token && result.state.status === "error" ? <InlineAlert tone="bad">{result.state.error}</InlineAlert> : null}
    </section>
  );
}
