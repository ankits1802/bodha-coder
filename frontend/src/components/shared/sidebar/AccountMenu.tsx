"use client";

import { useRouter } from "next/navigation";
import { Avatar } from "@/components/ui/Avatar";
import { MenuButton, type MenuItem } from "@/components/ui/MenuButton";
import type { User } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { ACCOUNT_PATH } from "@/lib/paths";
import { canReach } from "@/lib/roles";
import { signOut } from "@/lib/session/signOut";
import { SHARED_TEXT } from "../strings";
import { startTour } from "../tour/startTour";
import { TOUR_TEXT } from "../tour/strings";
import { REPLAY_TARGET } from "../tour/tourSteps";

interface AccountMenuProps {
  user: User;
  collapsed: boolean;
  onNavigate: () => void;
}

const EXPANDED =
  "flex w-full min-w-0 cursor-pointer items-center gap-2.5 rounded-nav px-2.5 py-1.5 text-left hover:bg-nav-hover aria-expanded:bg-nav-active";
const COLLAPSED = "mx-auto flex size-9 cursor-pointer items-center justify-center rounded-nav hover:bg-nav-hover aria-expanded:bg-nav-active";

export function accountItems(user: User, open: (path: string) => void): MenuItem[] {
  const words = SHARED_TEXT.account;
  const items: MenuItem[] = [];
  if (canReach(user, "account")) items.push({ key: "account", label: words.page, onSelect: () => open(ACCOUNT_PATH) });
  if (!user.billing_only) items.push({ key: "tour", label: TOUR_TEXT.take, onSelect: startTour });
  items.push({ key: "signOut", label: SHARED_TEXT.signOut, onSelect: () => void signOut() });
  return items;
}

export function AccountMenu({ user, collapsed, onNavigate }: AccountMenuProps) {
  const router = useRouter();
  const role = ROLE_LABELS[user.role];
  const items = accountItems(user, (path) => {
    onNavigate();
    router.push(path);
  });
  const trigger = collapsed ? (
    <Avatar name={user.name} />
  ) : (
    <>
      <Avatar name={user.name} />
      <span className="flex min-w-0 flex-col leading-tight">
        <span className="truncate text-subhead font-medium text-label">{user.name}</span>
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
        trigger={trigger}
        triggerClassName={collapsed ? COLLAPSED : EXPANDED}
      />
    </div>
  );
}
