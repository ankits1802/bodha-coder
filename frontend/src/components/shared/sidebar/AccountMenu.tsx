"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Avatar } from "@/components/ui/Avatar";
import { MenuButton } from "@/components/ui/MenuButton";
import type { PracticeChoice, User } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { signOut } from "@/lib/session/signOut";
import { LeavePracticeDialog } from "../practices/LeavePracticeDialog";
import { SHARED_TEXT } from "../strings";
import { startTour } from "../tour/startTour";
import { REPLAY_TARGET } from "../tour/tourSteps";
import { accountMenuItems } from "./accountMenuItems";
import { usePracticeSwitch } from "./usePracticeSwitch";

interface AccountMenuProps {
  user: User;
  collapsed: boolean;
  onNavigate: () => void;
}

const EXPANDED =
  "flex w-full min-w-0 cursor-pointer items-center gap-2.5 rounded-nav px-2.5 py-1.5 text-left hover:bg-nav-hover aria-expanded:bg-nav-active";
const COLLAPSED = "mx-auto flex size-9 cursor-pointer items-center justify-center rounded-nav hover:bg-nav-hover aria-expanded:bg-nav-active";

export function AccountMenu({ user, collapsed, onNavigate }: AccountMenuProps) {
  const router = useRouter();
  const currentId = user.practice?.id ?? null;
  const switching = usePracticeSwitch(currentId);
  const [leaving, setLeaving] = useState<PracticeChoice | null>(null);
  const role = ROLE_LABELS[user.role];
  const items = accountMenuItems(user, {
    open: (path) => {
      onNavigate();
      router.push(path);
    },
    switchTo: (practiceId) => void switching.choose(practiceId),
    leave: setLeaving,
    tour: startTour,
    signOut: () => void signOut(),
  });
  const trigger = collapsed ? (
    <Avatar name={user.name} />
  ) : (
    <>
      <Avatar name={user.name} />
      <span className="flex min-w-0 flex-col leading-tight">
        <span className="truncate text-subhead font-medium text-label">{user.name}</span>{" "}
        <span className="text-caption text-secondary">{role}</span>
      </span>
    </>
  );

  return (
    <div data-tour={REPLAY_TARGET} title={collapsed ? `${user.name} · ${role}` : undefined} className="border-t border-separator pt-2">
      <MenuButton
        label={SHARED_TEXT.account.menu(user.name, role)}
        items={items}
        align="auto"
        disabled={switching.pending}
        trigger={trigger}
        triggerClassName={collapsed ? COLLAPSED : EXPANDED}
      />
      {switching.error ? (
        <span role="alert" className="block px-2.5 pt-1 text-footnote text-bad-text">
          {switching.error}
        </span>
      ) : null}
      <LeavePracticeDialog practice={leaving} currentId={currentId} onClose={() => setLeaving(null)} />
    </div>
  );
}
