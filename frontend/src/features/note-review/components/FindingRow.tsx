import type { ReactNode } from "react";
import { CodeList } from "@/components/shared/CodeList";
import { CodeChange } from "@/components/ui/CodeChange";
import { StatusDot } from "@/components/ui/StatusDot";
import type { Finding } from "@/lib/api/types";
import { codeAfterLabel, findingStatus, quoteStatus, stringList, type QuoteCheck } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { EmDetails } from "./EmDetails";

interface FindingRowProps {
  finding: Finding;
  decision?: ReactNode;
  quote?: QuoteCheck | null;
  children?: ReactNode;
}

export function FindingRow({ finding, decision, quote = null, children }: FindingRowProps) {
  const status = findingStatus(finding);
  const quoted = quote ? quoteStatus(quote) : null;
  const options = stringList(finding.detail.options);
  return (
    <li className="flex flex-col gap-3 border-t border-hairline px-5 py-4 first:border-t-0">
      <div className="flex flex-wrap items-start justify-between gap-2.5">
        <div className="flex min-w-0 flex-[1_1_17rem] flex-col gap-1.25">
          <span className="flex flex-wrap items-center gap-2">
            <CodeChange
              before={finding.code_before}
              after={codeAfterLabel(finding)}
              addedLabel={REVIEW_TEXT.addedCode}
              changedLabel={REVIEW_TEXT.changedCode}
            />
            <span className="font-medium">{finding.title}</span>
            <StatusDot tone={status.tone}>{status.label}</StatusDot>
            {quoted ? <StatusDot tone={quoted.tone}>{quoted.label}</StatusDot> : null}
          </span>
          {finding.reasoning ? <span className="text-callout text-secondary">{finding.reasoning}</span> : null}
        </div>
        {decision}
      </div>
      {finding.kind === "em" ? <EmDetails finding={finding} /> : null}
      {options.length > 0 ? (
        <span className="flex flex-wrap items-center gap-2 text-callout text-secondary">
          {REVIEW_TEXT.options}
          <CodeList codes={options} />
        </span>
      ) : null}
      {children}
    </li>
  );
}
