import type { LaneCounts, ProviderReasonCounts, Role } from "@/lib/api/types";
import { LANE_VIEWS, type LaneView, type LaneViewKey } from "@/lib/labels";
import { canDo, type Action } from "@/lib/roles";
import type { ReviewScope } from "./useNoteData";

export interface LaneTotals {
  lanes: LaneCounts;
  provider_reasons: ProviderReasonCounts;
}

const WORK: Record<LaneViewKey, Action | null> = {
  approve: "approve",
  coder: "decide",
  questions: "ask",
  waiting_on_provider: null,
  compliance: "complianceDecision",
};

function waiting(view: LaneView, totals: LaneTotals): number {
  return view.reason ? totals.provider_reasons[view.reason].total : totals.lanes[view.lane].total;
}

function leftInScope(scope: ReviewScope, totals: LaneTotals): number {
  const split = LANE_VIEWS.find((view) => view.reason !== null && view.reason === scope.reason);
  if (split) return waiting(split, totals);
  return scope.lane ? totals.lanes[scope.lane].total : 0;
}

function works(view: LaneView, role: Role | null | undefined): boolean {
  const action = WORK[view.key];
  return action !== null && canDo(role, action);
}

function inScope(view: LaneView, scope: ReviewScope): boolean {
  return view.lane === scope.lane && (scope.reason === null || view.reason === scope.reason);
}

export function nextLaneView(totals: LaneTotals, scope: ReviewScope, role: Role | null | undefined): LaneView | null {
  if (leftInScope(scope, totals) > 0) return null;
  const at = LANE_VIEWS.findLastIndex((view) => inScope(view, scope));
  const start = at + 1;
  const ordered = [...LANE_VIEWS.slice(start), ...LANE_VIEWS.slice(0, start)];
  return ordered.find((view) => !inScope(view, scope) && works(view, role) && waiting(view, totals) > 0) ?? null;
}
