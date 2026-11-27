"use client";

import { useCallback, useState } from "react";

const STORAGE_KEY = "bodha.sidebar.collapsed";

function storedChoice(): boolean {
  try {
    return typeof window !== "undefined" && window.localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function remember(collapsed: boolean): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, String(collapsed));
  } catch {
    return;
  }
}

export function useSidebarCollapsed(): { collapsed: boolean; toggle: () => void } {
  const [collapsed, setCollapsed] = useState(storedChoice);
  const toggle = useCallback(() => {
    setCollapsed((current) => {
      remember(!current);
      return !current;
    });
  }, []);
  return { collapsed, toggle };
}
