"use client";

import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "@/lib/media";

const DURATION = 1400;

function animate(element: HTMLElement, target: number, suffix: string): () => void {
  let frame = 0;
  const start = performance.now();
  const step = (now: number) => {
    const progress = Math.min(1, (now - start) / DURATION);
    element.textContent = `${Math.round((1 - (1 - progress) ** 4) * target)}${suffix}`;
    if (progress < 1) frame = requestAnimationFrame(step);
  };
  frame = requestAnimationFrame(step);
  return () => cancelAnimationFrame(frame);
}

export function CountUp({ value }: { value: string }) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const element = ref.current;
    const match = /^(\d+)(.*)$/.exec(value);
    if (!element || !match || prefersReducedMotion() || typeof IntersectionObserver === "undefined") return;
    if (element.getBoundingClientRect().top < window.innerHeight) return;
    const target = Number(match[1]);
    const suffix = match[2] ?? "";
    element.textContent = `0${suffix}`;
    let stop = () => {};
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry?.isIntersecting) return;
      observer.disconnect();
      stop = animate(element, target, suffix);
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
      stop();
    };
  }, [value]);

  return (
    <>
      <span ref={ref} aria-hidden="true">
        {value}
      </span>
      <span className="sr-only">{value}</span>
    </>
  );
}
