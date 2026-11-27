"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { haptic } from "@/lib/haptics";
import { prefersReducedMotion } from "./progress";

const SCROLLED_AFTER = 8;

function jumpTo(event: MouseEvent): void {
  const anchor = (event.target as HTMLElement | null)?.closest("a");
  const hash = anchor?.getAttribute("href");
  if (!hash?.startsWith("#")) return;
  const target = document.getElementById(hash.slice(1));
  if (!target) return;
  event.preventDefault();
  haptic("select");
  target.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
  history.replaceState(null, "", hash);
}

export function NavShell({ label, className, children }: { label: string; className?: string; children: ReactNode }) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const update = () => {
      element.dataset.scrolled = String(window.scrollY > SCROLLED_AFTER);
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    element.addEventListener("click", jumpTo);
    return () => {
      window.removeEventListener("scroll", update);
      element.removeEventListener("click", jumpTo);
    };
  }, []);

  return (
    <nav ref={ref} aria-label={label} className={className} data-scrolled="false">
      {children}
    </nav>
  );
}
