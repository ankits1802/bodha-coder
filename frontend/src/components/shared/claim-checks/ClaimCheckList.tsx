import { CodeChip } from "@/components/ui/CodeChip";
import { StatusDot } from "@/components/ui/StatusDot";
import type { ClaimCheckItem } from "./claimCheckItems";
import { CLAIM_CHECK_TEXT } from "./strings";

function ItemRow({ item }: { item: ClaimCheckItem }) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
      <span className="inline-flex flex-wrap items-center gap-1.5">
        {item.codes.map((code) => (
          <CodeChip key={code} code={code} />
        ))}
        {item.detail ? <span className="text-footnote text-secondary">{item.detail}</span> : null}
      </span>
      <StatusDot tone={item.tone}>{item.status}</StatusDot>
    </li>
  );
}

export function ClaimCheckList({ items }: { items: ClaimCheckItem[] }) {
  return (
    <ul aria-label={CLAIM_CHECK_TEXT.heading} className="m-0 flex list-none flex-col gap-2.5 p-0">
      {items.map((item) => (
        <ItemRow key={item.key} item={item} />
      ))}
    </ul>
  );
}
