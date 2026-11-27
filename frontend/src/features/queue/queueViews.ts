import type { QueryChanges } from "@/hooks/useQueryParams";
import type { QueueViewFilters, QueueViews } from "@/lib/api/types";
import { LANE_VIEWS, type LaneViewKey } from "@/lib/labels";
import { QUEUE_TEXT } from "./strings";
import type { QueueFilters } from "./useQueueFilters";

export type LaneChoice = LaneViewKey | "all";

export interface ViewChoice {
  value: string;
  label: string;
  filters: QueueViewFilters;
}

const SAVED_PREFIX = "saved:";

export function currentFilters(filters: QueueFilters): QueueViewFilters {
  return {
    lane: filters.lane ?? null,
    reason: filters.reason ?? null,
    assigned: filters.assigned || null,
    provider_id: filters.providerId || null,
    overdue: filters.overdue,
    sort: filters.sort,
  };
}

export function sameFilters(first: QueueViewFilters, second: QueueViewFilters): boolean {
  return (
    first.lane === second.lane &&
    first.reason === second.reason &&
    first.assigned === second.assigned &&
    first.provider_id === second.provider_id &&
    first.overdue === second.overdue &&
    first.sort === second.sort
  );
}

export function viewChanges(filters: QueueViewFilters): QueryChanges {
  return {
    lane: filters.lane,
    reason: filters.reason,
    assigned: filters.assigned,
    provider_id: filters.provider_id,
    overdue: filters.overdue ? "1" : null,
    sort: filters.sort === "impact" ? "impact" : null,
    batch: null,
    offset: null,
  };
}

export function viewChoices(views: QueueViews): ViewChoice[] {
  return [
    ...views.builtin.map((view) => ({ value: view.key, label: QUEUE_TEXT.views.builtin[view.key], filters: view.filters })),
    ...views.saved.map((view) => ({ value: `${SAVED_PREFIX}${view.id}`, label: view.name, filters: view.filters })),
  ];
}

export function matchingView(choices: ViewChoice[], current: QueueViewFilters): string | null {
  return choices.find((choice) => sameFilters(choice.filters, current))?.value ?? null;
}

export function laneChoice(filters: Pick<QueueFilters, "lane" | "reason">): LaneChoice | null {
  if (!filters.lane) return "all";
  const view = LANE_VIEWS.find((item) => item.lane === filters.lane && (item.reason === null || item.reason === filters.reason));
  return view ? view.key : null;
}

export function laneChanges(choice: LaneChoice): QueryChanges {
  const view = LANE_VIEWS.find((item) => item.key === choice);
  return { lane: view?.lane ?? null, reason: view?.reason ?? null, offset: null };
}
