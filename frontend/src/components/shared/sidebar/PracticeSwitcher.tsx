"use client";

import { Chevron } from "@/components/ui/Chevron";
import { MenuButton, type MenuItem } from "@/components/ui/MenuButton";
import type { User } from "@/lib/api/types";
import { initialsOf } from "@/lib/format";
import { SHARED_TEXT } from "../strings";
import { usePracticeSwitch } from "./usePracticeSwitch";

interface PracticeSwitcherProps {
  user: User;
  collapsed: boolean;
}

const EXPANDED =
  "-ml-1 flex min-h-6 max-w-full min-w-0 cursor-pointer items-center gap-1.5 rounded-nav px-1 py-0.5 text-left text-footnote text-secondary hover:bg-nav-hover hover:text-label disabled:cursor-wait";
const COLLAPSED =
  "flex size-8 cursor-pointer items-center justify-center rounded-nav bg-avatar text-micro font-semibold text-label-soft hover:bg-nav-hover disabled:cursor-wait";

export function hasPracticeChoice(user: User): boolean {
  return user.practices.length > 1;
}

export function PracticeSwitcher({ user, collapsed }: PracticeSwitcherProps) {
  const current = user.practice?.id ?? null;
  const switching = usePracticeSwitch(current);
  const name = user.practice?.name ?? "";
  const words = SHARED_TEXT.practiceSwitcher;

  const items: MenuItem[] = user.practices.map((practice) => ({
    key: practice.id,
    label: practice.name,
    checked: practice.id === current,
    onSelect: () => void switching.choose(practice.id),
  }));
  const trigger = collapsed ? (
    <span aria-hidden="true" data-initials={initialsOf(name)} className="after:content-[attr(data-initials)]" />
  ) : (
    <>
      <span className="truncate">{name}</span>
      <Chevron direction="down" className="flex-none text-tertiary" />
    </>
  );

  return (
    <div className={`flex min-w-0 flex-col gap-1 ${collapsed ? "items-center" : ""}`}>
      <MenuButton
        label={words.label(name)}
        items={items}
        align="auto"
        disabled={switching.pending}
        trigger={trigger}
        triggerClassName={collapsed ? COLLAPSED : EXPANDED}
      />
      {switching.error ? (
        <span role="alert" className="text-footnote text-bad-text">
          {switching.error}
        </span>
      ) : null}
    </div>
  );
}
