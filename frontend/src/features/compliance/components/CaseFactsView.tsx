import { CodeChip } from "@/components/ui/CodeChip";
import type { CaseFacts } from "../complianceKinds";
import { COMPLIANCE_TEXT } from "../strings";

function Label({ children }: { children: string }) {
  return <div className="mb-1.5 text-caption text-secondary">{children}</div>;
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="m-0 flex flex-col gap-0.5 pl-4.5">
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  );
}

export function CaseFactsView({ facts }: { facts: CaseFacts }) {
  const changed = facts.billed !== null && facts.supported !== null && facts.billed !== facts.supported;
  return (
    <div className="flex flex-wrap gap-x-10 gap-y-6 px-5 py-4.5">
      {changed && facts.billed && facts.supported ? (
        <>
          <div>
            <Label>{COMPLIANCE_TEXT.billed}</Label>
            <CodeChip code={facts.billed} variant="old" />
          </div>
          <div>
            <Label>{COMPLIANCE_TEXT.supported}</Label>
            <CodeChip code={facts.supported} />
          </div>
        </>
      ) : null}
      {facts.inTheNote.length > 0 ? (
        <div className="min-w-0 flex-[1_1_20rem]">
          <Label>{COMPLIANCE_TEXT.inTheNote}</Label>
          <Bullets items={facts.inTheNote} />
        </div>
      ) : null}
      {facts.flagReason ? (
        <div className="min-w-0 flex-[1_1_20rem]">
          <Label>{COMPLIANCE_TEXT.flagReason}</Label>
          <p className="m-0">{facts.flagReason}</p>
        </div>
      ) : null}
      {facts.risks.length > 0 ? (
        <div className="min-w-0 flex-[1_1_20rem]">
          <Label>{COMPLIANCE_TEXT.risks}</Label>
          <Bullets
            items={facts.risks.map((risk) => (risk.severity ? COMPLIANCE_TEXT.severity(risk.severity, risk.title) : risk.title))}
          />
        </div>
      ) : null}
    </div>
  );
}
