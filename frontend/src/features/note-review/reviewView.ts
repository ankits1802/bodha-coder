import type { QueryChanges } from "@/hooks/useQueryParams";
import { HISTORY_OPEN } from "@/lib/paths";
import { REVIEW_FILTERS, type ReviewFilter } from "./reviewList";

const TAB_FILTERS: Record<string, ReviewFilter> = {
  codes: "changes",
  questions: "questions",
  wording: "guidance",
  audit: "risk",
  risk: "risk",
  history: "all",
};

export interface ReviewParams {
  filter: string | null;
  tab: string | null;
  history: string | null;
}

export interface ReviewView {
  filter: ReviewFilter;
  history: boolean;
}

function isFilter(value: string | null): value is ReviewFilter {
  return value !== null && (REVIEW_FILTERS as readonly string[]).includes(value);
}

export function reviewView({ filter, tab, history }: ReviewParams): ReviewView {
  const fromTab = tab !== null && Object.hasOwn(TAB_FILTERS, tab) ? TAB_FILTERS[tab] : undefined;
  return {
    filter: isFilter(filter) ? filter : (fromTab ?? "all"),
    history: history === HISTORY_OPEN || tab === "history",
  };
}

function filterParam(filter: ReviewFilter): string | null {
  return filter === "all" ? null : filter;
}

export function filterChanges(view: ReviewView, filter: ReviewFilter): QueryChanges {
  return { filter: filterParam(filter), tab: null, history: view.history ? HISTORY_OPEN : null };
}

export function historyChanges(view: ReviewView, open: boolean): QueryChanges {
  return { filter: filterParam(view.filter), tab: null, history: open ? HISTORY_OPEN : null };
}
