import Link from "next/link";
import { LANE_DOT_TONES } from "@/components/shared/noteStatus";
import { StatusDot } from "@/components/ui/StatusDot";
import type { LaneCount, LaneCounts, ProviderReasonCounts, Role } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { LANE_VIEWS, type LaneView } from "@/lib/labels";
import { canUse } from "@/lib/roles";
import { TODAY_TEXT } from "../strings";

const CELL = "-ml-px flex flex-col gap-1.5 border-l border-hairline px-5 py-4.5";

interface LaneCellsProps {
  counts: LaneCounts;
  reasons: ProviderReasonCounts;
  role: Role;
}

function laneHref(view: LaneView, role: Role): string | null {
  if (view.lane === "compliance" && canUse(role, "compliance")) return "/compliance";
  if (!canUse(role, "queue")) return null;
  return view.reason ? `/queue?lane=${view.lane}&reason=${view.reason}` : `/queue?lane=${view.lane}`;
}

function CellBody({ view, count }: { view: LaneView; count: LaneCount }) {
  return (
    <>
      <StatusDot tone={LANE_DOT_TONES[view.lane]}>{view.label}</StatusDot>
      <span className="text-stat-lg font-semibold tracking-title tabular-nums">{formatCount(count.total)}</span>
      <span className="text-subhead text-secondary">{TODAY_TEXT.dueSoon(formatCount(count.due_soon))}</span>
    </>
  );
}

export function LaneCells({ counts, reasons, role }: LaneCellsProps) {
  return (
    <section
      aria-label={TODAY_TEXT.waitingLabel}
      className="grid grid-cols-[repeat(auto-fit,minmax(11rem,1fr))] overflow-hidden rounded-panel bg-surface shadow-panel"
    >
      {LANE_VIEWS.map((view) => {
        const href = laneHref(view, role);
        const count = view.reason ? reasons[view.reason] : counts[view.lane];
        return href ? (
          <Link key={view.key} href={href} className={`${CELL} hover:bg-row-hover`}>
            <CellBody view={view} count={count} />
          </Link>
        ) : (
          <div key={view.key} className={CELL}>
            <CellBody view={view} count={count} />
          </div>
        );
      })}
    </section>
  );
}
