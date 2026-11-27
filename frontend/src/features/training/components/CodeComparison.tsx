import type { ReactNode } from "react";
import { CodeList } from "@/components/shared/CodeList";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { ClaimElements, TrainingFeedback } from "@/lib/api/types";
import { TRAINING_TEXT } from "../strings";

type Element = keyof ClaimElements;

const ELEMENTS: readonly Element[] = ["em", "icd", "modifiers"];

function codesOf(elements: ClaimElements, element: Element): string[] {
  const value = elements[element];
  if (Array.isArray(value)) return value;
  return value ? [value] : [];
}

function matchesClaim(feedback: TrainingFeedback, element: Element): boolean {
  return feedback.agreement.claim[element].match;
}

function Gaps({ feedback }: { feedback: TrainingFeedback }) {
  const { missing, extra } = feedback.agreement.claim.icd;
  const parts: ReactNode[] = [];
  if (missing.length > 0) parts.push(<span key="missing">{TRAINING_TEXT.missing} <CodeList codes={missing} /></span>);
  if (extra.length > 0) parts.push(<span key="extra">{TRAINING_TEXT.extra} <CodeList codes={extra} /></span>);
  if (parts.length === 0) return null;
  return <div className="flex flex-wrap gap-4 px-4 pb-4 text-footnote text-secondary">{parts}</div>;
}

export function CodeComparison({ feedback }: { feedback: TrainingFeedback }) {
  const words = TRAINING_TEXT.comparisonColumns;
  return (
    <>
      <Table label={TRAINING_TEXT.comparisonLabel} minWidth="md">
        <thead>
          <tr>
            <Th>{words.element}</Th>
            <Th>{words.yours}</Th>
            <Th>{words.claim}</Th>
            <Th>{words.bodha}</Th>
          </tr>
        </thead>
        <tbody>
          {ELEMENTS.map((element) => (
            <Tr key={element}>
              <Td className="font-medium">{TRAINING_TEXT.elements[element]}</Td>
              <Td>
                <span className="flex flex-col gap-1.5">
                  <CodeList codes={codesOf(feedback.answer, element)} />
                  <StatusDot tone={matchesClaim(feedback, element) ? "ok" : "warn"}>
                    {matchesClaim(feedback, element) ? TRAINING_TEXT.match : TRAINING_TEXT.differs}
                  </StatusDot>
                </span>
              </Td>
              <Td>
                <CodeList codes={codesOf(feedback.claim, element)} />
              </Td>
              <Td>
                <CodeList codes={codesOf(feedback.bodha, element)} />
              </Td>
            </Tr>
          ))}
        </tbody>
      </Table>
      <Gaps feedback={feedback} />
    </>
  );
}
