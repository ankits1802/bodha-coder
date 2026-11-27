import { Panel } from "@/components/ui/Panel";
import { StatusDot } from "@/components/ui/StatusDot";
import type { SealVerification } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { DocumentCheck } from "./DocumentCheck";
import { VERIFY_TEXT } from "./strings";

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 border-t border-separator py-2.5 first:border-t-0">
      <dt className="text-subhead text-secondary">{label}</dt>
      <dd className="m-0 text-body break-all">{value}</dd>
    </div>
  );
}

export function VerifyResult({ result }: { result: SealVerification }) {
  return (
    <Panel aria-label={VERIFY_TEXT.resultLabel} className="flex flex-col gap-3 px-5 py-4.5">
      <div role="status" className="flex flex-col gap-1.5">
        <StatusDot tone={result.valid ? "ok" : "bad"} className="text-headline font-semibold">
          {result.valid ? VERIFY_TEXT.valid : VERIFY_TEXT.invalid}
        </StatusDot>
        {result.problems.map((problem) => (
          <span key={problem} className="text-subhead text-secondary">
            {VERIFY_TEXT.problems[problem]}
          </span>
        ))}
      </div>
      <dl className="m-0">
        <Fact label={VERIFY_TEXT.event} value={VERIFY_TEXT.events[result.event]} />
        <Fact label={VERIFY_TEXT.practice} value={result.practice_name} />
        <Fact label={VERIFY_TEXT.signedBy} value={`${result.signer_name} (${result.signer_title})`} />
        <Fact label={VERIFY_TEXT.signed} value={formatDateTime(result.signed_at)} />
        <Fact label={VERIFY_TEXT.document} value={result.document_sha256 ?? VERIFY_TEXT.noDocument} />
        <Fact label={VERIFY_TEXT.envelope} value={result.envelope_sha256} />
      </dl>
      {result.document_sha256 ? <DocumentCheck expected={result.document_sha256} /> : null}
    </Panel>
  );
}
