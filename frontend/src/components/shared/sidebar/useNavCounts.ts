"use client";

import { useEffect, useState } from "react";
import { getToday } from "@/lib/api/work";
import type { CountKey } from "./navItems";

export type NavCounts = Partial<Record<CountKey, number>>;

export function useNavCounts(enabled: boolean, pathname: string): NavCounts {
  const [counts, setCounts] = useState<NavCounts>({});

  useEffect(() => {
    if (!enabled) return;
    let live = true;
    getToday().then(
      (today) => {
        if (live) setCounts({ queue: today.waiting, compliance: today.lanes.compliance.total });
      },
      () => {
        if (live) setCounts({});
      },
    );
    return () => {
      live = false;
    };
  }, [enabled, pathname]);

  return enabled ? counts : {};
}
