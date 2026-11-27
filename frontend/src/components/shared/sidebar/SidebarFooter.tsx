"use client";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import type { User } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { signOut } from "@/lib/session/signOut";
import { SHARED_TEXT } from "../strings";
import { ActionEntry } from "./NavEntry";

export function SidebarFooter({ user, collapsed }: { user: User; collapsed: boolean }) {
  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-2 border-t border-separator pt-3">
        <span title={`${user.name} · ${ROLE_LABELS[user.role]}`}>
          <Avatar name={user.name} />
        </span>
        <ActionEntry icon="signOut" label={SHARED_TEXT.signOut} collapsed onClick={() => void signOut()} />
      </div>
    );
  }
  return (
    <>
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
    </>
  );
}
