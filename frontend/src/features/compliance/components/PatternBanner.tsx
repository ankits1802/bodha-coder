import { Panel } from "@/components/ui/Panel";
import type { CompliancePattern } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { COMPLIANCE_TEXT } from "../strings";

const PATTERN_MIN = 2;

export function PatternBanner({ patterns, total }: { patterns: CompliancePattern[]; total: number }) {
  const top = patterns[0];
  if (!top || top.count < PATTERN_MIN) return null;
  return (
    <Panel aria-label={COMPLIANCE_TEXT.patternLabel} className="flex flex-wrap items-baseline gap-x-3.5 gap-y-1.5 px-4.5 py-4">
      <span className="font-semibold">{top.provider_name}</span>
      <span className="text-secondary">{COMPLIANCE_TEXT.pattern(formatCount(top.count), formatCount(total))}</span>
    </Panel>
  );
}
