"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import type { User } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { canDo, canUse, homeFor } from "@/lib/roles";
import { signOut } from "@/lib/session/signOut";
import { openOverlay } from "../overlays";
import { SHARED_TEXT } from "../strings";
import { NavIcon } from "./NavIcon";
import { NAV_GROUP_ORDER, isActive, navFor, type NavItem } from "./navItems";
import { useNavCounts, type NavCounts } from "./useNavCounts";

interface SidebarProps {
  user: User;
  onNavigate: () => void;
}

function NavEntry({ item, active, count, onNavigate }: { item: NavItem; active: boolean; count?: number; onNavigate: () => void }) {
  return (
    <li>
      <Link
        href={item.href}
        onClick={onNavigate}
        aria-current={active ? "page" : undefined}
        className={`flex h-8 items-center gap-2.5 rounded-nav px-2.5 text-callout tracking-snug text-label hover:bg-nav-hover ${active ? "bg-nav-active font-medium" : ""}`}
      >
        <NavIcon name={item.icon} />
        {item.label}
        {count !== undefined ? (
          <span className={`ml-auto text-caption tabular-nums ${active ? "text-label-soft" : "text-tertiary"}`}>{count}</span>
        ) : null}
      </Link>
    </li>
  );
}

const ENTRY_CLASSES = "flex h-8 items-center gap-2.5 rounded-nav px-2.5 text-callout tracking-snug text-label hover:bg-nav-hover";

function SearchEntry({ onNavigate }: { onNavigate: () => void }) {
  const open = () => {
    onNavigate();
    openOverlay("search");
  };
  return (
    <button type="button" onClick={open} className={`mt-3 w-full cursor-pointer text-left ${ENTRY_CLASSES}`}>
      <NavIcon name="search" />
      {SHARED_TEXT.nav.search}
    </button>
  );
}

function countFor(item: NavItem, counts: NavCounts): number | undefined {
  return item.count ? counts[item.count] : undefined;
}

export function Sidebar({ user, onNavigate }: SidebarProps) {
  const pathname = usePathname();
  const items = navFor(user.role);
  const counts = useNavCounts(canUse(user.role, "queue"), pathname);
  const words = SHARED_TEXT.nav;
  const groups = NAV_GROUP_ORDER.map((group) => ({ group, entries: items.filter((item) => item.group === group) })).filter(
    (entry) => entry.entries.length > 0,
  );

  return (
    <div className="flex h-full flex-col border-r border-separator bg-sidebar px-3 pt-5.5 pb-4">
      <div className="flex flex-col gap-0.5 px-2.5">
        <Link href={homeFor(user.role)} onClick={onNavigate} className="text-body-lg font-semibold tracking-snug text-label">
          {SHARED_TEXT.brand}
        </Link>
        <span className="text-footnote text-secondary">{user.practice?.name ?? SHARED_TEXT.platformAdministration}</span>
      </div>
      {canDo(user.role, "search") ? <SearchEntry onNavigate={onNavigate} /> : null}
      <nav aria-label={user.role === "hq" ? words.platformLabel : words.mainLabel} className="mt-1.5 flex flex-col">
        {groups.map(({ group, entries }) => (
          <div key={group}>
            <h2 className="m-0 px-2.5 pt-4.5 pb-1.5 font-sans text-micro font-semibold text-tertiary">{words.groups[group]}</h2>
            <ul className="m-0 flex list-none flex-col gap-px p-0">
              {entries.map((item) => (
                <NavEntry
                  key={item.key}
                  item={item}
                  active={isActive(item, pathname)}
                  count={countFor(item, counts)}
                  onNavigate={onNavigate}
                />
              ))}
            </ul>
          </div>
        ))}
      </nav>
      <div className="mt-auto flex flex-col gap-2 pt-6">
        {canUse(user.role, "help") ? (
          <Link
            href="/help"
            onClick={onNavigate}
            aria-current={pathname === "/help" ? "page" : undefined}
            className={`${ENTRY_CLASSES} ${pathname === "/help" ? "bg-nav-active font-medium" : ""}`}
          >
            <NavIcon name="help" />
            {words.help}
          </Link>
        ) : null}
        <div className="flex items-center gap-2.5 border-t border-separator px-2.5 pt-3">
          <Avatar name={user.name} />
          <span className="flex min-w-0 flex-col leading-tight">
            <span className="truncate text-subhead font-medium">{user.name}</span>
            <span className="text-caption text-secondary">{ROLE_LABELS[user.role]}</span>
          </span>
        </div>
        <Button variant="plain" size="sm" className="self-start" onClick={() => void signOut()}>
          {SHARED_TEXT.signOut}
        </Button>
      </div>
    </div>
  );
}
