import { StatusDot } from "@/components/ui/StatusDot";
import type { SsoTrialResult } from "@/lib/api/types";
import { SSO_TEXT } from "./strings";

function answer(value: boolean): string {
  return value ? SSO_TEXT.yes : SSO_TEXT.no;
}

function reasonText(reason: string | null): string {
  if (reason === null) return SSO_TEXT.none;
  return SSO_TEXT.reasons[reason] ?? reason;
}

export function TestResult({ result }: { result: SsoTrialResult }) {
  const rows: [string, string][] = result.passed
    ? [
        [SSO_TEXT.testDomain, result.domain ?? SSO_TEXT.none],
        [SSO_TEXT.testInDomains, answer(result.in_domains)],
        [SSO_TEXT.testAccount, answer(result.account)],
        [SSO_TEXT.testName, answer(result.name_found)],
        [SSO_TEXT.testTwoStep, answer(result.mfa)],
        [SSO_TEXT.testContext, result.context_class ?? SSO_TEXT.none],
      ]
    : [[SSO_TEXT.testReason, reasonText(result.reason)]];
  return (
    <div role="status" className="flex flex-col gap-2">
      <StatusDot tone={result.passed ? "ok" : "bad"}>{result.passed ? SSO_TEXT.testPassed : SSO_TEXT.testFailed}</StatusDot>
      <dl className="m-0 grid grid-cols-1 gap-1 text-body sm:grid-cols-[max-content_1fr] sm:gap-x-4">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-secondary">{label}</dt>
            <dd className="m-0 break-all">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
