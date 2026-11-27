"use client";

import { useEffect, useState } from "react";

export const SETTLE_MS = 250;

export function useSettled<T>(value: T, delay = SETTLE_MS): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return settled;
}
