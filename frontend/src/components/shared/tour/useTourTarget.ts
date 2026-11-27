"use client";

import { useEffect, useState } from "react";
import { prefersReducedMotion } from "@/lib/media";
import type { Box, Size } from "./tourPlacement";

export const TARGET_WAIT_MS = 2000;
const TARGET_POLL_MS = 100;

export type TargetStatus = "none" | "searching" | "found" | "missing";

export interface TourTarget {
  status: TargetStatus;
  box: Box | null;
  view: Size | null;
}

interface Search {
  target: string;
  element: HTMLElement | null;
}

interface Measure {
  element: HTMLElement;
  box: Box;
  view: Size;
}

function viewport(): Size {
  return { width: window.innerWidth, height: window.innerHeight };
}

function boxOf(element: HTMLElement): Box {
  const rect = element.getBoundingClientRect();
  return { top: rect.top, left: rect.left, width: rect.width, height: rect.height };
}

function findShown(target: string): HTMLElement | null {
  const element = document.querySelector<HTMLElement>(`[data-tour="${target}"]`);
  if (!element) return null;
  const { width, height } = boxOf(element);
  return width > 0 && height > 0 ? element : null;
}

function bringIntoView(element: HTMLElement): void {
  if (typeof element.scrollIntoView !== "function") return;
  element.scrollIntoView({ block: "nearest", inline: "nearest", behavior: prefersReducedMotion() ? "auto" : "smooth" });
}

function useTargetElement(target: string | null): Search | null {
  const [search, setSearch] = useState<Search | null>(null);
  useEffect(() => {
    if (target === null) return;
    const started = Date.now();
    let timer = 0;
    const look = () => {
      const element = findShown(target);
      if (element || Date.now() - started >= TARGET_WAIT_MS) setSearch({ target, element });
      else timer = window.setTimeout(look, TARGET_POLL_MS);
    };
    timer = window.setTimeout(look, 0);
    return () => window.clearTimeout(timer);
  }, [target]);
  return search !== null && search.target === target ? search : null;
}

function useTargetBox(element: HTMLElement | null): Measure | null {
  const [measure, setMeasure] = useState<Measure | null>(null);
  useEffect(() => {
    if (!element) return;
    let frame = 0;
    const update = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => setMeasure({ element, box: boxOf(element), view: viewport() }));
    };
    bringIntoView(element);
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(update);
    observer?.observe(element);
    observer?.observe(document.documentElement);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
      observer?.disconnect();
    };
  }, [element]);
  return measure !== null && measure.element === element ? measure : null;
}

export function useTourTarget(target: string | null): TourTarget {
  const search = useTargetElement(target);
  const measure = useTargetBox(search?.element ?? null);
  if (target === null) return { status: "none", box: null, view: null };
  if (search === null) return { status: "searching", box: null, view: null };
  if (search.element === null) return { status: "missing", box: null, view: null };
  if (measure === null) return { status: "searching", box: null, view: null };
  return { status: "found", box: measure.box, view: measure.view };
}
