export const PRACTICE_TABS = ["people", "plan", "spend", "activity", "places"] as const;
export type PracticeTab = (typeof PRACTICE_TABS)[number];

const DEFAULT_TAB: PracticeTab = "people";

function isPracticeTab(value: string | null): value is PracticeTab {
  return value !== null && (PRACTICE_TABS as readonly string[]).includes(value);
}

export function tabFrom(value: string | null): PracticeTab {
  return isPracticeTab(value) ? value : DEFAULT_TAB;
}

export function practiceHref(practiceId: string, tab?: PracticeTab): string {
  const path = `/hq/practices/${encodeURIComponent(practiceId)}`;
  return tab ? `${path}?tab=${tab}` : path;
}
