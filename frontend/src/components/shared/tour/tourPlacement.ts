export interface Box {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface Size {
  width: number;
  height: number;
}

export type Side = "right" | "below" | "above" | "left";

export interface CardSpot {
  top: number;
  left: number;
  side: Side;
}

export const SPOT_PADDING = 6;
export const CARD_GAP = 12;
export const VIEW_EDGE = 16;
const SIDES: readonly Side[] = ["right", "below", "above", "left"];

function clamp(value: number, low: number, high: number): number {
  return Math.min(Math.max(value, low), Math.max(low, high));
}

export function spotlightBox(target: Box): Box {
  return {
    top: target.top - SPOT_PADDING,
    left: target.left - SPOT_PADDING,
    width: target.width + SPOT_PADDING * 2,
    height: target.height + SPOT_PADDING * 2,
  };
}

export function isOnScreen(box: Box, view: Size): boolean {
  if (box.width <= 0 || box.height <= 0) return false;
  return box.top < view.height && box.left < view.width && box.top + box.height > 0 && box.left + box.width > 0;
}

function spotOn(side: Side, spot: Box, card: Size, view: Size): CardSpot {
  const middleTop = clamp(spot.top + (spot.height - card.height) / 2, VIEW_EDGE, view.height - card.height - VIEW_EDGE);
  const middleLeft = clamp(spot.left + (spot.width - card.width) / 2, VIEW_EDGE, view.width - card.width - VIEW_EDGE);
  const places: Record<Side, Omit<CardSpot, "side">> = {
    right: { top: middleTop, left: spot.left + spot.width + CARD_GAP },
    left: { top: middleTop, left: spot.left - CARD_GAP - card.width },
    below: { top: spot.top + spot.height + CARD_GAP, left: middleLeft },
    above: { top: spot.top - CARD_GAP - card.height, left: middleLeft },
  };
  return { ...places[side], side };
}

function fits(spot: CardSpot, card: Size, view: Size): boolean {
  const insideX = spot.left >= VIEW_EDGE && spot.left + card.width <= view.width - VIEW_EDGE;
  const insideY = spot.top >= VIEW_EDGE && spot.top + card.height <= view.height - VIEW_EDGE;
  return insideX && insideY;
}

export function cardSpot(spot: Box, card: Size, view: Size): CardSpot | null {
  for (const side of SIDES) {
    const candidate = spotOn(side, spot, card, view);
    if (fits(candidate, card, view)) return candidate;
  }
  return null;
}
