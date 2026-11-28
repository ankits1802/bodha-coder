"use client";

import { useEffect } from "react";
import { loadRemote } from "@/hooks/remoteCache";
import { getAppearance } from "@/lib/api/account";
import { APPEARANCE_KEEP_SECONDS, APPEARANCE_KEY, applyAppearance } from "@/lib/appearance";
import { useSession } from "@/lib/session/useSession";

export function AppearanceSync() {
  const userId = useSession().user?.id ?? null;

  useEffect(() => {
    if (userId === null) return;
    let live = true;
    loadRemote(APPEARANCE_KEY, getAppearance, APPEARANCE_KEEP_SECONDS).then(
      (appearance) => {
        if (live) applyAppearance(appearance);
      },
      () => undefined,
    );
    return () => {
      live = false;
    };
  }, [userId]);

  return null;
}
