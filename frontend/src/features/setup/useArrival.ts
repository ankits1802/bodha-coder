"use client";

import { useEffect, useEffectEvent } from "react";

export function useArrival(arrived: boolean, onArrived: () => void): void {
  const handle = useEffectEvent(onArrived);
  useEffect(() => {
    if (arrived) handle();
  }, [arrived]);
}
