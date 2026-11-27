import { PLAN_PATH, canReach, type Area, type SessionUser } from "@/lib/roles";
import { SHARED_TEXT } from "../strings";
import type { NavIconName } from "./NavIcon";

export type NavGroup = "work" | "practice" | "platform";
export type CountKey = "queue" | "compliance";

export interface NavItem {
  key: string;
  area: Area;
  href: string;
  label: string;
  icon: NavIconName;
  group: NavGroup;
  count?: CountKey;
}

const words = SHARED_TEXT.nav;

export const NAV_ITEMS: readonly NavItem[] = [
  { key: "today", area: "today", href: "/today", label: words.today, icon: "calendar", group: "work" },
  { key: "upload", area: "upload", href: "/upload", label: words.upload, icon: "upload", group: "work" },
  { key: "queue", area: "queue", href: "/queue", label: words.queue, icon: "list", group: "work", count: "queue" },
  { key: "compliance", area: "compliance", href: "/compliance", label: words.compliance, icon: "shield", group: "work", count: "compliance" },
  { key: "billing", area: "billing", href: "/billing", label: words.billing, icon: "card", group: "work" },
  { key: "remittances", area: "billing", href: "/remittances", label: words.remittances, icon: "inbox", group: "work" },
  { key: "training", area: "queue", href: "/training", label: words.training, icon: "book", group: "work" },
  { key: "insights", area: "insights", href: "/insights", label: words.insights, icon: "bars", group: "practice" },
  { key: "quality", area: "compliance", href: "/quality", label: words.quality, icon: "gauge", group: "practice" },
  { key: "setup", area: "setup", href: "/setup", label: words.setup, icon: "house", group: "practice" },
  { key: "team", area: "team", href: "/team", label: words.team, icon: "people", group: "practice" },
  { key: "plan", area: "plan", href: PLAN_PATH, label: words.plan, icon: "receipt", group: "practice" },
  { key: "security", area: "security", href: "/security", label: words.security, icon: "lock", group: "practice" },
  { key: "hqOverview", area: "hq", href: "/hq", label: words.hqOverview, icon: "gauge", group: "platform" },
  { key: "hqPractices", area: "hq", href: "/hq/practices", label: words.hqPractices, icon: "house", group: "platform" },
  { key: "hqActivity", area: "hq", href: "/hq/activity", label: words.hqActivity, icon: "clock", group: "platform" },
  { key: "hqDemos", area: "hq", href: "/hq/demos", label: words.hqDemos, icon: "inbox", group: "platform" },
  { key: "hqTeam", area: "hq", href: "/hq/team", label: words.hqTeam, icon: "people", group: "platform" },
  { key: "hqSecurity", area: "hq", href: "/hq/security", label: words.hqSecurity, icon: "lock", group: "platform" },
];

export const NAV_GROUP_ORDER: readonly NavGroup[] = ["work", "practice", "platform"];

export function navFor(user: SessionUser): NavItem[] {
  return NAV_ITEMS.filter((item) => canReach(user, item.area));
}

export function isActive(item: NavItem, pathname: string): boolean {
  if (item.href === "/hq") return pathname === "/hq";
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}
