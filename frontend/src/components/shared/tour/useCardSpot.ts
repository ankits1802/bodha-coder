"use client";

import { useEffect, useState, type RefObject } from "react";
import { cardSpot, isOnScreen, spotlightBox, type Box, type CardSpot, type Size } from "./tourPlacement";
import type { TourTarget } from "./useTourTarget";

const CARD_ESTIMATE: Size = { width: 320, height: 168 };

export interface Placement {
  spotlight: Box | null;
  card: CardSpot | null;
}

const CENTRED: Placement = { spotlight: null, card: null };

function useCardSize(card: RefObject<HTMLDivElement | null>): Size {
  const [size, setSize] = useState<Size>(CARD_ESTIMATE);
  useEffect(() => {
    const node = card.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => {
      const next = { width: node.offsetWidth, height: node.offsetHeight };
      if (next.width === 0) return;
      setSize((current) => (current.width === next.width && current.height === next.height ? current : next));
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [card]);
  return size;
}

export function useCardSpot(target: TourTarget, card: RefObject<HTMLDivElement | null>): Placement {
  const size = useCardSize(card);
  if (target.box === null || target.view === null) return CENTRED;
  const spotlight = spotlightBox(target.box);
  if (!isOnScreen(spotlight, target.view)) return CENTRED;
  const spot = cardSpot(spotlight, size, target.view);
  return spot ? { spotlight, card: spot } : CENTRED;
}
