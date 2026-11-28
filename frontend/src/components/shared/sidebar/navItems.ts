import type { Role } from "@/lib/api/types";
import { ACCESS_LOG_PATH, SECURITY_SETTINGS_PATH, SETUP_PATH, TEAM_PATH, USAGE_PATH } from "@/lib/paths";
import { PLAN_PATH, canReach, type Area, type SessionUser } from "@/lib/roles";
import { SHARED_TEXT } from "../strings";
import type { NavIconName } from "./NavIcon";

export type NavGroup = "work" | "practice" | "platform";
export type CountKey = "queue" | "compliance" | "inbox";

export interface NavTab {
  key: string;
  area: Area;
  href: string;
  label: string;
}

export interface NavItem {
  key: string;
  area: Area;
  href: string;
  label: string;
  icon: NavIconName;
  group: NavGroup;
  count?: CountKey;
  tabs?: readonly NavTab[];
  hiddenFor?: readonly Role[];
}

const words = SHARED_TEXT.nav;
const tabs = SHARED_TEXT.tabs;

const BILLING_TABS: readonly NavTab[] = [
  { key: "readyToBill", area: "billing", href: "/billing", label: tabs.readyToBill },
  { key: "remittances", area: "billing", href: "/billing/remittances", label: tabs.remittances },
];

const INSIGHT_TABS: readonly NavTab[] = [
  { key: "overview", area: "insights", href: "/insights", label: tabs.overview },
  { key: "quality", area: "compliance", href: "/insights/quality", label: tabs.quality },
  { key: "accessLog", area: "accessLog", href: ACCESS_LOG_PATH, label: tabs.accessLog },
  { key: "usage", area: "usage", href: USAGE_PATH, label: tabs.usage },
];

const SETTINGS_TABS: readonly NavTab[] = [
  { key: "setup", area: "setup", href: SETUP_PATH, label: tabs.setup },
  { key: "team", area: "team", href: TEAM_PATH, label: tabs.team },
  { key: "plan", area: "plan", href: PLAN_PATH, label: tabs.plan },
  { key: "security", area: "security", href: SECURITY_SETTINGS_PATH, label: tabs.security },
];

export const NAV_ITEMS: readonly NavItem[] = [
  { key: "today", area: "today", href: "/today", label: words.today, icon: "calendar", group: "work" },
  { key: "inbox", area: "inbox", href: "/inbox", label: words.inbox, icon: "bell", group: "work", count: "inbox" },
  { key: "upload", area: "upload", href: "/upload", label: words.upload, icon: "upload", group: "work" },
  { key: "queue", area: "queue", href: "/queue", label: words.queue, icon: "list", group: "work", count: "queue", hiddenFor: ["biller"] },
  { key: "compliance", area: "compliance", href: "/compliance", label: words.compliance, icon: "shield", group: "work", count: "compliance" },
  { key: "billing", area: "billing", href: "/billing", label: words.billing, icon: "card", group: "work", tabs: BILLING_TABS },
  { key: "insights", area: "insights", href: "/insights", label: words.insights, icon: "bars", group: "practice", tabs: INSIGHT_TABS },
  { key: "settings", area: "settings", href: "/settings", label: words.settings, icon: "gear", group: "practice", tabs: SETTINGS_TABS },
  { key: "hqOverview", area: "hq", href: "/hq", label: words.hqOverview, icon: "gauge", group: "platform" },
  { key: "hqPractices", area: "hq", href: "/hq/practices", label: words.hqPractices, icon: "house", group: "platform" },
  { key: "hqOrganizations", area: "hq", href: "/hq/organizations", label: words.hqOrganizations, icon: "building", group: "platform" },
  { key: "hqSpend", area: "hq", href: "/hq/spend", label: words.hqSpend, icon: "bars", group: "platform" },
  { key: "hqUsage", area: "hq", href: "/hq/usage", label: words.hqUsage, icon: "timer", group: "platform" },
  { key: "hqActivity", area: "hq", href: "/hq/activity", label: words.hqActivity, icon: "clock", group: "platform" },
  { key: "hqDemos", area: "hq", href: "/hq/demos", label: words.hqDemos, icon: "inbox", group: "platform" },
  { key: "hqTeam", area: "hq", href: "/hq/team", label: words.hqTeam, icon: "people", group: "platform" },
  { key: "hqSecurity", area: "hq", href: "/hq/security", label: words.hqSecurity, icon: "lock", group: "platform" },
];

export const NAV_GROUP_ORDER: readonly NavGroup[] = ["work", "practice", "platform"];

function shownTo(user: SessionUser, item: NavItem): boolean {
  return canReach(user, item.area) && !item.hiddenFor?.includes(user.role);
}

function withReachableTabs(user: SessionUser, item: NavItem): NavItem | null {
  if (!item.tabs) return item;
  const reachable = item.tabs.filter((tab) => canReach(user, tab.area));
  const first = reachable[0];
  return first ? { ...item, href: first.href, tabs: reachable } : null;
}

export function navFor(user: SessionUser): NavItem[] {
  return NAV_ITEMS.filter((item) => shownTo(user, item))
    .map((item) => withReachableTabs(user, item))
    .filter((item): item is NavItem => item !== null);
}

function isUnder(href: string, pathname: string): boolean {
  if (href === "/hq") return pathname === "/hq";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function isActive(item: NavItem, pathname: string): boolean {
  return [item.href, ...(item.tabs ?? []).map((tab) => tab.href)].some((href) => isUnder(href, pathname));
}

export function activeTab(tabList: readonly NavTab[], pathname: string): NavTab | null {
  const matching = tabList.filter((tab) => isUnder(tab.href, pathname));
  return matching.reduce<NavTab | null>((best, tab) => (best === null || tab.href.length > best.href.length ? tab : best), null);
}

export function navItemFor(user: SessionUser, key: string): NavItem | null {
  return navFor(user).find((item) => item.key === key) ?? null;
}
