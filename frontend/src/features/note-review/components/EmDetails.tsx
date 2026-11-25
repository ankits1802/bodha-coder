import type { Finding, MdmElements } from "@/lib/api/types";
import { emDetail } from "../findings";
import { REVIEW_TEXT } from "../strings";

const PARTS: (keyof MdmElements)[] = ["problems", "data", "risk"];

function MdmGrid({ mdm }: { mdm: MdmElements }) {
  return (
    <dl className="m-0 grid grid-cols-1 overflow-hidden rounded-field bg-muted-panel sm:grid-cols-3">
      {PARTS.map((part) => (
        <div key={part} className="-mt-px border-t border-separator px-3.5 py-2.5 sm:mt-0 sm:-ml-px sm:border-t-0 sm:border-l">
          <dt className="text-caption text-secondary">{REVIEW_TEXT.mdm[part]}</dt>
          <dd className="m-0 font-semibold">{mdm[part].level}</dd>
          {mdm[part].reason ? <dd className="m-0 text-footnote text-secondary">{mdm[part].reason}</dd> : null}
        </div>
      ))}
    </dl>
  );
}

export function EmDetails({ finding }: { finding: Finding }) {
  const detail = emDetail(finding);
  return (
    <>
      {detail.mdm ? <MdmGrid mdm={detail.mdm} /> : null}
      {detail.basis === "Time" && detail.timeMinutes !== null ? (
        <p className="m-0 text-callout text-secondary">{REVIEW_TEXT.mdm.time(detail.timeMinutes)}</p>
      ) : null}
      {detail.nextLevelNeeds.length > 0 ? (
        <div className="text-callout">
          <span className="font-medium">{REVIEW_TEXT.nextLevel}</span>
          <ul className="m-0 mt-1 pl-4.5 text-secondary">
            {detail.nextLevelNeeds.map((need) => (
              <li key={need}>{need}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {detail.alternativeCode ? (
        <p className="m-0 text-callout text-secondary">{REVIEW_TEXT.alternative(detail.alternativeCode)}</p>
      ) : null}
    </>
  );
}
