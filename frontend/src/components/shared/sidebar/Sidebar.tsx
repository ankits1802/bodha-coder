"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { User } from "@/lib/api/types";
import { canReach, canSearch, canSearchPlatform, homeFor } from "@/lib/roles";
import { openOverlay } from "../overlays";
import { SHARED_TEXT } from "../strings";
import { ActionEntry, NavEntry } from "./NavEntry";
import { NavIcon } from "./NavIcon";
import { NAV_GROUP_ORDER, isActive, navFor, type NavItem } from "./navItems";
import { PracticeSwitcher, hasPracticeChoice } from "./PracticeSwitcher";
import { SidebarFooter } from "./SidebarFooter";
import { useInboxCount } from "./inboxCount";
import { useNavCounts, type NavCounts } from "./useNavCounts";

interface SidebarProps {
  user: User;
  collapsed: boolean;
  onToggle: () => void;
  onNavigate: () => void;
}

function countFor(item: NavItem, counts: NavCounts): number | undefined {
  return item.count ? counts[item.count] : undefined;
}

function Header({ user, collapsed, onToggle, onNavigate }: SidebarProps) {
  const label = collapsed ? SHARED_TEXT.expandSidebar : SHARED_TEXT.collapseSidebar;
  const toggle = (
    <button
      type="button"
      onClick={onToggle}
      aria-label={label}
      aria-expanded={!collapsed}
      title={`${label} ( [ )`}
      className="hidden size-7 flex-none cursor-pointer items-center justify-center rounded-nav text-secondary hover:bg-nav-hover hover:text-label lg:flex"
    >
      <NavIcon name="sidebar" />
    </button>
  );
  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-2">
        <Link href={homeFor(user)} onClick={onNavigate} title={SHARED_TEXT.brand} className="text-body-lg font-bold text-label">
          <span aria-hidden="true">B</span>
          <span className="sr-only">{SHARED_TEXT.brand}</span>
        </Link>
        {hasPracticeChoice(user) ? <PracticeSwitcher user={user} collapsed /> : null}
        {toggle}
      </div>
    );
  }
  return (
    <div className="flex items-start justify-between gap-2 pl-2.5">
      <div className="flex min-w-0 flex-col gap-0.5">
        <Link href={homeFor(user)} onClick={onNavigate} className="text-body-lg font-semibold tracking-snug text-label">
          {SHARED_TEXT.brand}
        </Link>
        {hasPracticeChoice(user) ? (
          <PracticeSwitcher user={user} collapsed={false} />
        ) : (
          <span className="truncate text-footnote text-secondary">{user.practice?.name ?? SHARED_TEXT.platformAdministration}</span>
        )}
      </div>
      {toggle}
    </div>
  );
}

export function Sidebar(props: SidebarProps) {
  const { user, collapsed, onNavigate } = props;
  const pathname = usePathname();
  const items = navFor(user);
  const counts = { ...useNavCounts(canReach(user, "queue"), pathname), inbox: useInboxCount(canReach(user, "inbox"), pathname) };
  const words = SHARED_TEXT.nav;
  const groups = NAV_GROUP_ORDER.map((group) => ({ group, entries: items.filter((item) => item.group === group) })).filter(
    (entry) => entry.entries.length > 0,
  );
  const search = () => {
    onNavigate();
    openOverlay("search");
  };

  return (
    <div className={`flex h-full flex-col border-r border-separator bg-sidebar pt-5.5 pb-4 ${collapsed ? "px-2" : "px-3"}`}>
      <Header {...props} />
      {canSearch(user) || canSearchPlatform(user) ? (
        <div className="mt-3">
          <ActionEntry icon="search" label={words.search} collapsed={collapsed} onClick={search} />
        </div>
      ) : null}
      <nav aria-label={user.role === "hq" ? words.platformLabel : words.mainLabel} className="mt-1.5 flex flex-col">
        {groups.map(({ group, entries }) => (
          <div key={group}>
            <h2 className={collapsed ? "sr-only" : "m-0 px-2.5 pt-4.5 pb-1.5 font-sans text-micro font-semibold text-tertiary"}>
              {words.groups[group]}
            </h2>
            {collapsed ? <div aria-hidden="true" className="mx-2 my-2.5 border-t border-separator" /> : null}
            <ul className="m-0 flex list-none flex-col gap-px p-0">
              {entries.map((item) => (
                <NavEntry
                  key={item.key}
                  href={item.href}
                  icon={item.icon}
                  label={item.label}
                  active={isActive(item, pathname)}
                  collapsed={collapsed}
                  count={countFor(item, counts)}
                  onNavigate={onNavigate}
                />
              ))}
            </ul>
          </div>
        ))}
      </nav>
      <div className="mt-auto flex flex-col gap-2 pt-6">
        {canReach(user, "help") ? (
          <ul className="m-0 list-none p-0">
            <NavEntry href="/help" icon="help" label={words.help} active={pathname === "/help"} collapsed={collapsed} onNavigate={onNavigate} />
          </ul>
        ) : null}
        <SidebarFooter user={user} collapsed={collapsed} />
      </div>
    </div>
  );
}
