"use client";

import { useEffect, useRef, type ReactNode, type RefObject } from "react";
import { hasFinePointer, prefersReducedMotion } from "./progress";

function observe(entries: IntersectionObserverEntry[]): void {
  for (const entry of entries) {
    const target = entry.target as HTMLElement;
    if (target.hasAttribute("data-live")) target.dataset.onscreen = String(entry.isIntersecting);
    if (entry.isIntersecting && target.dataset.state === "waiting") target.dataset.state = "shown";
  }
}

function useReveal(root: RefObject<HTMLElement | null>): void {
  useEffect(() => {
    const element = root.current;
    if (!element || prefersReducedMotion() || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(observe, { rootMargin: "0px 0px -8% 0px" });
    for (const target of element.querySelectorAll<HTMLElement>("[data-reveal], [data-live]")) {
      if (target.hasAttribute("data-reveal") && target.getBoundingClientRect().top > window.innerHeight) {
        target.dataset.state = "waiting";
      }
      observer.observe(target);
    }
    return () => observer.disconnect();
  }, [root]);
}

function usePointerField(root: RefObject<HTMLElement | null>): void {
  useEffect(() => {
    const element = root.current;
    if (!element || prefersReducedMotion() || !hasFinePointer()) return;
    let frame = 0;
    let x = 0;
    let y = 0;
    const paint = () => {
      frame = 0;
      element.style.setProperty("--mx", ((x / window.innerWidth) * 2 - 1).toFixed(3));
      element.style.setProperty("--my", ((y / window.innerHeight) * 2 - 1).toFixed(3));
      element.style.setProperty("--px", `${x}px`);
      element.style.setProperty("--py", `${y}px`);
    };
    const move = (event: PointerEvent) => {
      x = event.clientX;
      y = event.clientY;
      if (!frame) frame = requestAnimationFrame(paint);
    };
    window.addEventListener("pointermove", move, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", move);
    };
  }, [root]);
}

export function MotionRoot({ className, children }: { className?: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useReveal(ref);
  usePointerField(ref);
  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
