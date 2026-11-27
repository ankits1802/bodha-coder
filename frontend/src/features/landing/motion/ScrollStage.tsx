"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { actFor, enterProgress, pinProgress, prefersReducedMotion, throughProgress, type ProgressMode } from "./progress";

interface ScrollStageProps {
  mode: ProgressMode;
  acts?: number;
  className?: string;
  children: ReactNode;
}

function measure(element: HTMLElement, mode: ProgressMode): number {
  const rect = element.getBoundingClientRect();
  const viewport = window.innerHeight;
  if (mode === "pin") return pinProgress(rect.top, rect.height, viewport);
  if (mode === "through") return throughProgress(rect.top, rect.height, viewport);
  return enterProgress(rect.top, viewport);
}

export function ScrollStage({ mode, acts, className, children }: ScrollStageProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    if (prefersReducedMotion()) {
      element.style.setProperty("--p", "1");
      return;
    }
    let frame = 0;
    const update = () => {
      frame = 0;
      const progress = measure(element, mode);
      element.style.setProperty("--p", progress.toFixed(4));
      if (acts) element.dataset.act = String(actFor(progress, acts));
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [mode, acts]);

  return (
    <div ref={ref} className={className} data-act={acts ? "0" : undefined}>
      {children}
    </div>
  );
}
