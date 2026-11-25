import type { Finding, NoteDetail } from "@/lib/api/types";
import { textValue } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { TabSection } from "./TabSection";

function GapItem({ finding }: { finding: Finding }) {
  const words = REVIEW_TEXT.wording;
  const recommendation = textValue(finding.detail.recommendation);
  const suggested = textValue(finding.detail.suggested_text);
  const current = finding.evidence[0];
  return (
    <li className="flex flex-col gap-1.5 border-t border-hairline py-3 first:border-t-0 first:pt-0">
      <span className="flex flex-wrap items-baseline gap-x-3">
        <span className="font-medium">{finding.title}</span>
        {finding.severity ? <span className="text-footnote text-secondary">{words.priority(finding.severity)}</span> : null}
      </span>
      {current ? (
        <span className="text-callout text-secondary">
          {words.current} <q>{current}</q>
        </span>
      ) : null}
      {recommendation ? <span className="text-callout">{recommendation}</span> : null}
      {suggested ? (
        <figure className="m-0 rounded-field bg-muted-panel px-3.5 py-2.5">
          <figcaption className="text-caption text-secondary">{words.suggested}</figcaption>
          <p className="m-0 whitespace-pre-wrap">{suggested}</p>
        </figure>
      ) : null}
    </li>
  );
}

export function WordingTab({ detail }: { detail: NoteDetail }) {
  const words = REVIEW_TEXT.wording;
  const gaps = detail.findings.filter((item) => item.kind === "cdi_gap");
  const guidance = detail.analysis?.cdi.summaryGuidance ?? null;
  const links = detail.analysis?.cdi.codeLinkingOpportunities ?? [];
  if (gaps.length === 0 && !guidance && links.length === 0) {
    return <p className="m-0 px-5 py-6 text-secondary">{words.none}</p>;
  }
  return (
    <>
      {guidance ? (
        <TabSection title={words.guidance}>
          <p className="m-0">{guidance}</p>
        </TabSection>
      ) : null}
      {gaps.length > 0 ? (
        <TabSection title={words.suggested}>
          <ul className="m-0 list-none p-0">
            {gaps.map((finding) => (
              <GapItem key={finding.key} finding={finding} />
            ))}
          </ul>
        </TabSection>
      ) : null}
      {links.length > 0 ? (
        <TabSection title={words.linking}>
          <ul className="m-0 flex flex-col gap-1.5 pl-4.5">
            {links.map((link) => (
              <li key={`${link.diagnosis}-${link.suggestion}`}>
                <span className="font-medium">{link.diagnosis}</span>
                <span className="block text-callout text-secondary">{link.suggestion}</span>
              </li>
            ))}
          </ul>
        </TabSection>
      ) : null}
    </>
  );
}
