"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useEffectEvent, useRef } from "react";
import { isWideScreen } from "@/lib/media";

function currentPage(): string {
  return `${window.location.pathname}${window.location.search}`;
}

export function useTourPage(path: string | null, onMenu: (open: boolean) => void): () => void {
  const router = useRouter();
  const start = useRef<string | null>(null);
  const openedMenu = useRef(false);
  const showMenu = useEffectEvent(() => onMenu(true));

  useEffect(() => {
    start.current = currentPage();
    if (isWideScreen()) return;
    openedMenu.current = true;
    showMenu();
  }, []);

  useEffect(() => {
    if (path !== null && path !== window.location.pathname) router.push(path);
  }, [path, router]);

  return useCallback(() => {
    if (openedMenu.current) onMenu(false);
    if (start.current !== null && start.current !== currentPage()) router.push(start.current);
  }, [onMenu, router]);
}
