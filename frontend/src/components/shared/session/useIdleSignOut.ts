"use client";

import { useEffect } from "react";
import type { User } from "@/lib/api/types";
import { idleMinutesFor } from "@/lib/roles";
import { startIdleTimer } from "@/lib/session/idle";
import { signOut } from "@/lib/session/signOut";

export function useIdleSignOut(user: User | null): void {
  const minutes = user ? idleMinutesFor(user.role, user.practice?.idle_minutes) : null;

  useEffect(() => {
    if (minutes === null) return;
    return startIdleTimer({
      minutes,
      onIdle: () => {
        void signOut("idle");
      },
    });
  }, [minutes]);
}
