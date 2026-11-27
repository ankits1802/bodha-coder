import { useId } from "react";
import { LegalText } from "./LegalText";
import type { LegalTable } from "./types";

const WIDE_FROM_COLUMNS = 3;

export function LegalTableView({ table }: { table: LegalTable }) {
  const captionId = useId();
  const wide = table.columns.length >= WIDE_FROM_COLUMNS;
  return (
    <div role="region" aria-labelledby={captionId} tabIndex={0} className="overflow-x-auto rounded-panel border border-separator">
      <table className={`w-full border-collapse text-left text-body leading-normal ${wide ? "min-w-160 print:min-w-0" : ""}`}>
        <caption id={captionId} className="border-b border-separator px-4 py-3 text-left text-subhead font-semibold text-label">
          {table.caption}
        </caption>
        <thead>
          <tr>
            {table.columns.map((column) => (
              <th key={column} scope="col" className="border-b border-separator bg-muted-panel px-4 py-2.5 text-caption font-semibold text-secondary">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row) => (
            <tr key={row.join("|")} className="align-top last:[&>*]:border-b-0">
              {row.map((cell, index) =>
                index === 0 ? (
                  <th key={index} scope="row" className="border-b border-hairline px-4 py-3 font-semibold text-label">
                    <LegalText text={cell} />
                  </th>
                ) : (
                  <td key={index} className="border-b border-hairline px-4 py-3 text-label-soft">
                    <LegalText text={cell} />
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
