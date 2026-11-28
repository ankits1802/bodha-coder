import { LANE_DOT_TONES } from "@/components/shared/noteStatus";
import { StatCell, StatGrid } from "@/components/ui/StatGrid";
import { urlFor } from "@/lib/api/client";
import type { LaneCounts, ProviderReasonCounts } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { LANE_VIEWS, type LaneView } from "@/lib/labels";
import { COMPLIANCE_PATH } from "@/lib/paths";
import { canReach, reachableHref, type SessionUser } from "@/lib/roles";
import { TODAY_TEXT } from "../strings";

interface LaneCellsProps {
  counts: LaneCounts;
  reasons: ProviderReasonCounts;
  user: SessionUser;
}

function laneHref(view: LaneView, user: SessionUser): string | null {
  if (view.lane === "compliance" && canReach(user, "compliance")) return COMPLIANCE_PATH;
  return reachableHref(user, "queue", urlFor("/queue", { lane: view.lane, reason: view.reason }));
}

export function LaneCells({ counts, reasons, user }: LaneCellsProps) {
  return (
    <StatGrid label={TODAY_TEXT.waitingLabel} size="lg">
      {LANE_VIEWS.map((view) => {
        const count = view.reason ? reasons[view.reason] : counts[view.lane];
        return (
          <StatCell
            key={view.key}
            label={view.label}
            tone={LANE_DOT_TONES[view.lane]}
            value={formatCount(count.total)}
            note={TODAY_TEXT.dueSoon(formatCount(count.due_soon))}
            href={laneHref(view, user)}
          />
        );
      })}
    </StatGrid>
  );
}
