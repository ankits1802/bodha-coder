"use client";

import { useEffect, useState, type RefObject } from "react";
import { floatingStyle, type FloatAlign, type FloatingStyle } from "./floating";

interface Frame {
  height: number;
  width: number;
  style: FloatingStyle;
}

export interface Floating {
  style: FloatingStyle | null;
  width: number;
  show: (height: number) => void;
  hide: () => void;
}

function frameFor(anchor: HTMLElement, height: number, align: FloatAlign): Frame {
  const rect = anchor.getBoundingClientRect();
  const viewport = { width: window.innerWidth, height: window.innerHeight };
  return { height, width: rect.width, style: floatingStyle(rect, viewport, height, align) };
}

export function useFloating(
  anchor: RefObject<HTMLElement | null>,
  panel: RefObject<HTMLElement | null>,
  align: FloatAlign = "auto",
): Floating {
  const [frame, setFrame] = useState<Frame | null>(null);
  const shown = frame !== null;

  useEffect(() => {
    if (!shown) return;
    const within = (target: EventTarget | null, element: HTMLElement | null) => target instanceof Node && Boolean(element?.contains(target));
    const onPointer = (event: MouseEvent) => {
      if (!within(event.target, panel.current) && !within(event.target, anchor.current)) setFrame(null);
    };
    const follow = (event: Event) => {
      if (within(event.target, panel.current)) return;
      setFrame((current) => (current && anchor.current ? frameFor(anchor.current, current.height, align) : current));
    };
    document.addEventListener("mousedown", onPointer);
    window.addEventListener("resize", follow);
    window.addEventListener("scroll", follow, true);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      window.removeEventListener("resize", follow);
      window.removeEventListener("scroll", follow, true);
    };
  }, [shown, anchor, panel, align]);

  return {
    style: frame ? frame.style : null,
    width: frame ? frame.width : 0,
    show: (height) => {
      if (anchor.current) setFrame(frameFor(anchor.current, height, align));
    },
    hide: () => setFrame(null),
  };
}
