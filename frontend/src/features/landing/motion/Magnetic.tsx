"use client";

import { useRef, type PointerEvent, type ReactNode } from "react";
import { haptic } from "@/lib/haptics";
import { hasFinePointer, prefersReducedMotion } from "@/lib/media";

const PULL = 0.28;
const LIMIT = 14;

function limited(value: number): number {
  return Math.max(-LIMIT, Math.min(LIMIT, value));
}

export function Magnetic({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLSpanElement>(null);

  function follow(event: PointerEvent<HTMLSpanElement>): void {
    const element = ref.current;
    if (!element || !hasFinePointer() || prefersReducedMotion()) return;
    const rect = element.getBoundingClientRect();
    const x = limited((event.clientX - rect.left - rect.width / 2) * PULL);
    const y = limited((event.clientY - rect.top - rect.height / 2) * PULL);
    element.style.transform = `translate3d(${x}px, ${y}px, 0)`;
  }

  function release(): void {
    if (ref.current) ref.current.style.transform = "";
  }

  return (
    <span
      ref={ref}
      onPointerMove={follow}
      onPointerLeave={release}
      onPointerDown={() => haptic("tap")}
      className="-m-4 inline-flex p-4 transition-transform duration-500 ease-[cubic-bezier(0.2,0.9,0.2,1)] will-change-transform"
    >
      {children}
    </span>
  );
}
