"use client";

import { useState } from "react";
import { isoDateInZone, localIsoDate } from "@/lib/dates";
import { useSession } from "@/lib/session/useSession";

export function usePracticeToday(): string {
  const { user } = useSession();
  const [now] = useState(() => new Date());
  const zone = user?.practice?.time_zone;
  return zone ? isoDateInZone(now, zone) : localIsoDate(now);
}
