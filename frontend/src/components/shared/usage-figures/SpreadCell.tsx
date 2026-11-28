import { Td } from "@/components/ui/Table";
import type { UsageSpread } from "@/lib/api/types";
import { FORMAT_WORDS } from "@/lib/format";
import { USAGE_TEXT } from "./strings";

interface SpreadCellProps {
  spread: UsageSpread | null;
  format: (value: number) => string;
}

export function SpreadCell({ spread, format }: SpreadCellProps) {
  return (
    <Td className="text-right tabular-nums">
      {spread ? (
        <>
          <span className="block">{format(spread.median)}</span>
          <span className="block text-caption text-secondary">{USAGE_TEXT.spread(format(spread.p25), format(spread.p75))}</span>
        </>
      ) : (
        FORMAT_WORDS.empty
      )}
    </Td>
  );
}
