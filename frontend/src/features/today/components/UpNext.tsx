import Link from "next/link";
import { NoteLinkRow } from "@/components/shared/NoteLinkRow";
import { SHARED_TEXT } from "@/components/shared/strings";
import { CodeChange } from "@/components/ui/CodeChange";
import { CodeChip } from "@/components/ui/CodeChip";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import type { QueueRow } from "@/lib/api/types";
import { codeHint } from "../codeHint";
import { TODAY_TEXT } from "../strings";

function SuggestedCode({ row }: { row: QueueRow }) {
  const hint = codeHint(row.billed, row.suggested);
  if (!hint) return null;
  if (hint.before) {
    return (
      <CodeChange before={hint.before} after={hint.after} addedLabel={SHARED_TEXT.codeAdded} changedLabel={SHARED_TEXT.codeChanged} />
    );
  }
  return (
    <span>
      <span className="sr-only">{TODAY_TEXT.suggested}</span>
      <CodeChip code={hint.after} variant="new" />
    </span>
  );
}

export function UpNext({ rows }: { rows: QueueRow[] }) {
  return (
    <section aria-labelledby="today-up-next" className="flex min-w-0 flex-[3_1_28rem] flex-col gap-3">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id="today-up-next" className="m-0 text-title3 font-semibold tracking-headline">
          {TODAY_TEXT.upNext}
        </h2>
        <Link href="/queue" className="text-body text-secondary hover:underline">
          {TODAY_TEXT.seeAll}
        </Link>
      </div>
      <Panel as="div">
        {rows.length === 0 ? (
          <EmptyState title={TODAY_TEXT.nothingNext} />
        ) : (
          <ul className="m-0 list-none divide-y divide-hairline p-0">
            {rows.map((row) => (
              <NoteLinkRow key={row.id} row={row} lane="coder" codes={<SuggestedCode row={row} />} />
            ))}
          </ul>
        )}
      </Panel>
    </section>
  );
}
