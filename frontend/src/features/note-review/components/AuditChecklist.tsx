import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import type { AnalysisView, CodingComplianceCheck } from "@/lib/api/types";
import { REVIEW_TEXT } from "../strings";
import { TabSection } from "./TabSection";

const CHECK_TONES: Record<CodingComplianceCheck["status"], StatusTone> = { Pass: "ok", Fail: "bad", Warning: "warn" };

interface CheckLineProps {
  tone: StatusTone;
  word: string;
  title: string;
  note?: string | null;
}

function CheckLine({ tone, word, title, note }: CheckLineProps) {
  return (
    <li className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
      <span className="min-w-0 flex-[1_1_14rem]">
        <span className="font-medium">{title}</span>
        {note ? <span className="block text-callout text-secondary">{note}</span> : null}
      </span>
      <StatusDot tone={tone}>{word}</StatusDot>
    </li>
  );
}

export function AuditChecklist({ audit }: { audit: AnalysisView["audit"] }) {
  const words = REVIEW_TEXT.audit;
  const checkWords = { Pass: words.pass, Fail: words.fail, Warning: words.warning };
  return (
    <>
      {audit.requiredElements?.length ? (
        <TabSection title={words.required}>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {audit.requiredElements.map((item) => (
              <CheckLine
                key={item.element}
                tone={item.present ? "ok" : "bad"}
                word={item.present ? words.present : words.missing}
                title={item.element}
                note={item.deficiency}
              />
            ))}
          </ul>
        </TabSection>
      ) : null}
      {audit.codingCompliance?.length ? (
        <TabSection title={words.checks}>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {audit.codingCompliance.map((item) => (
              <CheckLine
                key={item.check}
                tone={CHECK_TONES[item.status]}
                word={checkWords[item.status]}
                title={item.check}
                note={item.finding}
              />
            ))}
          </ul>
        </TabSection>
      ) : null}
      {audit.cmsCDICompliance?.length ? (
        <TabSection title={words.cms}>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {audit.cmsCDICompliance.map((item) => (
              <CheckLine
                key={item.standard}
                tone={item.compliant ? "ok" : "bad"}
                word={item.compliant ? words.compliant : words.notCompliant}
                title={item.standard}
                note={item.note}
              />
            ))}
          </ul>
        </TabSection>
      ) : null}
    </>
  );
}
