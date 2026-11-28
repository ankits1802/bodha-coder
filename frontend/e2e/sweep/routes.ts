import { NAV_ITEMS, type NavItem } from "../../src/components/shared/sidebar/navItems";
import type { PracticeRole } from "../../src/lib/api/types";
import { PRACTICE_ROLES, canUse, type Area } from "../../src/lib/roles";
import type { Who } from "./world";

export interface Route {
  path: string;
  area: Area;
}

const OFF_NAV_ROUTES: readonly Route[] = [
  { path: "/account", area: "account" },
  { path: "/help", area: "help" },
  { path: "/practices/new", area: "account" },
];

function routesOf(item: NavItem): Route[] {
  if (!item.tabs) return [{ path: item.href, area: item.area }];
  return item.tabs.map((tab) => ({ path: tab.href, area: tab.area }));
}

export const PRACTICE_ROUTES: readonly Route[] = [
  ...NAV_ITEMS.filter((item) => item.group !== "platform").flatMap(routesOf),
  ...OFF_NAV_ROUTES,
];

export const HQ_ROUTES: readonly string[] = NAV_ITEMS.filter((item) => item.group === "platform").map((item) => item.href);

export function rolesFor(area: Area): Who[] {
  return PRACTICE_ROLES.filter((role: PracticeRole) => canUse(role, area));
}
