import type { TourKey, TourRecord } from "@/lib/api/types";
import { SECURITY_SETTINGS_PATH } from "@/lib/paths";
import { canDo, canReach, canSearch, type SessionUser } from "@/lib/roles";
import type { NavIconName } from "../sidebar/NavIcon";
import { navFor, type NavItem } from "../sidebar/navItems";
import { SHARED_TEXT } from "../strings";
import { TOUR_TEXT, type TourExtra } from "./strings";

export const TOUR_VERSION = 2;
export const REPLAY_TARGET = "tour";
export const SEARCH_TARGET: NavIconName = "search";
const HELP_PATH = "/help";
const QUEUE_PATH = "/queue";

export interface TourStep {
  key: string;
  title: string;
  line: string;
  target: string | null;
  path: string | null;
}

export function tourKeyFor(user: SessionUser): TourKey {
  return user.role === "hq" ? "hq" : "practice";
}

export function isTourDue(records: readonly TourRecord[], tour: TourKey): boolean {
  return !records.some((record) => record.tour === tour && record.version >= TOUR_VERSION);
}

function areaStep(key: string, title: string, href: string): TourStep {
  return { key, title, line: TOUR_TEXT.areas[key] ?? "", target: href, path: href };
}

function extraStep(key: TourExtra, target: string | null, path: string): TourStep {
  return { key, ...TOUR_TEXT.extras[key], target, path };
}

function reviewSteps(user: SessionUser): TourStep[] {
  const steps: TourStep[] = [];
  if (canDo(user.role, "decide")) steps.push(extraStep("decide", null, QUEUE_PATH));
  steps.push(extraStep("evidence", null, QUEUE_PATH));
  if (canDo(user.role, "ask")) steps.push(extraStep("ask", null, QUEUE_PATH));
  return steps;
}

function accessLogSteps(user: SessionUser, item: NavItem): TourStep[] {
  const reachable = item.tabs?.some((tab) => tab.href === SECURITY_SETTINGS_PATH) ?? false;
  return reachable && canDo(user.role, "manageSecurity") ? [extraStep("accessLog", item.href, SECURITY_SETTINGS_PATH)] : [];
}

const FOLLOW_UPS: Readonly<Record<string, (user: SessionUser, item: NavItem) => TourStep[]>> = {
  queue: reviewSteps,
  settings: accessLogSteps,
};

function stepsForArea(item: NavItem, user: SessionUser): TourStep[] {
  return [areaStep(item.key, item.label, item.href), ...(FOLLOW_UPS[item.key]?.(user, item) ?? [])];
}

export function tourStepsFor(user: SessionUser): [TourStep, ...TourStep[]] {
  const welcome: TourStep = { key: "welcome", ...TOUR_TEXT.welcome[tourKeyFor(user)], target: null, path: null };
  const search = canSearch(user)
    ? [{ key: "search", title: SHARED_TEXT.nav.search, line: TOUR_TEXT.areas.search ?? "", target: SEARCH_TARGET, path: null }]
    : [];
  const help = canReach(user, "help") ? [areaStep("help", SHARED_TEXT.nav.help, HELP_PATH)] : [];
  const replay: TourStep = { key: "replay", ...TOUR_TEXT.replay[tourKeyFor(user)], target: REPLAY_TARGET, path: null };
  return [welcome, ...search, ...navFor(user).flatMap((item) => stepsForArea(item, user)), ...help, replay];
}
