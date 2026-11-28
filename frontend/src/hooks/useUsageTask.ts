"use client";

import { useEffect, useMemo, useRef } from "react";
import type { UsageTask } from "@/lib/api/types";
import { usageRecorder } from "@/lib/usage/session";

export interface UsageTaskHandle {
  complete: () => void;
  decided: (count: number) => void;
}

export function useUsageTask(task: UsageTask): UsageTaskHandle {
  const handle = useRef(0);

  useEffect(() => {
    handle.current = usageRecorder.start(task);
    return () => {
      usageRecorder.end(handle.current, "left");
      handle.current = 0;
    };
  }, [task]);

  return useMemo(
    () => ({
      complete: () => {
        if (handle.current === 0) return;
        usageRecorder.end(handle.current, "completed");
        handle.current = usageRecorder.start(task);
      },
      decided: (count: number) => usageRecorder.decided(handle.current, count),
    }),
    [task],
  );
}
