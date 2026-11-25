import Link from "next/link";
import { LANE_DOT_TONES } from "@/components/shared/noteStatus";
import { StatusDot } from "@/components/ui/StatusDot";
import type { Lane, LaneCounts, Role } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { LANE_LABELS, LANE_ORDER } from "@/lib/labels";
import { canUse } from "@/lib/roles";
import { TODAY_TEXT } from "../strings";

const CELL = "-ml-px flex flex-col gap-1.5 border-l border-hairline px-5 py-4.5";

function laneHref(lane: Lane, role: Role): string | null {
  if (lane === "compliance" && canUse(role, "compliance")) return "/compliance";
  return canUse(role, "queue") ? `/queue?lane=${lane}` : null;
}

function CellBody({ lane, counts }: { lane: Lane; counts: LaneCounts }) {
  const count = counts[lane];
  return (
    <>
      <StatusDot tone={LANE_DOT_TONES[lane]}>{LANE_LABELS[lane]}</StatusDot>
      <span className="text-stat-lg font-semibold tracking-title tabular-nums">{formatCount(count.total)}</span>
      <span className="text-subhead text-secondary">{TODAY_TEXT.dueSoon(formatCount(count.due_soon))}</span>
    </>
  );
}

export function LaneCells({ counts, role }: { counts: LaneCounts; role: Role }) {
  return (
    <section
      aria-label={TODAY_TEXT.waitingLabel}
      className="grid grid-cols-[repeat(auto-fit,minmax(11rem,1fr))] overflow-hidden rounded-panel bg-surface shadow-panel"
    >
      {LANE_ORDER.map((lane) => {
        const href = laneHref(lane, role);
        return href ? (
          <Link key={lane} href={href} className={`${CELL} hover:bg-row-hover`}>
            <CellBody lane={lane} counts={counts} />
          </Link>
        ) : (
          <div key={lane} className={CELL}>
            <CellBody lane={lane} counts={counts} />
          </div>
        );
      })}
    </section>
  );
}
