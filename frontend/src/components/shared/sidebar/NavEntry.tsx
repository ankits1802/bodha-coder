"use client";

import Link from "next/link";
import { NavIcon, type NavIconName } from "./NavIcon";

const BASE = "relative flex h-8 items-center gap-2.5 rounded-nav text-callout tracking-snug text-label hover:bg-nav-hover";

export function entryClasses(collapsed: boolean, active: boolean): string {
  const shape = collapsed ? "mx-auto w-9 justify-center px-0" : "px-2.5";
  return `${BASE} ${shape} ${active ? "bg-nav-active font-medium" : ""}`;
}

interface EntryProps {
  href: string;
  icon: NavIconName;
  label: string;
  active: boolean;
  collapsed: boolean;
  count?: number;
  onNavigate: () => void;
}

function Count({ count, active, collapsed }: { count: number; active: boolean; collapsed: boolean }) {
  if (collapsed) {
    if (count === 0) return null;
    return (
      <span className="absolute -top-0.5 -right-0.5 min-w-4 rounded-full bg-dark px-1 text-center text-micro leading-4 font-semibold text-white tabular-nums">
        {count > 99 ? "99+" : count}
      </span>
    );
  }
  return <span className={`ml-auto text-caption tabular-nums ${active ? "text-label-soft" : "text-tertiary"}`}>{count}</span>;
}

export function NavEntry({ href, icon, label, active, collapsed, count, onNavigate }: EntryProps) {
  return (
    <li>
      <Link
        href={href}
        onClick={onNavigate}
        aria-current={active ? "page" : undefined}
        title={collapsed ? label : undefined}
        className={entryClasses(collapsed, active)}
      >
        <NavIcon name={icon} />
        <span className={collapsed ? "sr-only" : undefined}>{label}</span>
        {count !== undefined ? <Count count={count} active={active} collapsed={collapsed} /> : null}
      </Link>
    </li>
  );
}

export function ActionEntry({ icon, label, collapsed, onClick }: { icon: NavIconName; label: string; collapsed: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={collapsed ? label : undefined}
      className={`cursor-pointer text-left ${collapsed ? "" : "w-full"} ${entryClasses(collapsed, false)}`}
    >
      <NavIcon name={icon} />
      <span className={collapsed ? "sr-only" : undefined}>{label}</span>
    </button>
  );
}
