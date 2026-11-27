import { describe, expect, it } from "vitest";
import { cardSpot, isOnScreen, spotlightBox, type Box, type Size } from "../tourPlacement";

const DESKTOP: Size = { width: 1280, height: 800 };
const PHONE: Size = { width: 375, height: 812 };
const CARD: Size = { width: 320, height: 168 };
const PHONE_CARD: Size = { width: 343, height: 168 };

function overlaps(card: { top: number; left: number }, size: Size, spot: Box): boolean {
  const apartX = card.left + size.width <= spot.left || spot.left + spot.width <= card.left;
  const apartY = card.top + size.height <= spot.top || spot.top + spot.height <= card.top;
  return !(apartX || apartY);
}

describe("spotlightBox", () => {
  it("pads the target by six pixels on every side", () => {
    expect(spotlightBox({ top: 120, left: 12, width: 208, height: 32 })).toEqual({ top: 114, left: 6, width: 220, height: 44 });
  });
});

describe("cardSpot", () => {
  it("puts the card to the right of a sidebar entry on a desktop", () => {
    const spot = spotlightBox({ top: 120, left: 12, width: 208, height: 32 });
    expect(cardSpot(spot, CARD, DESKTOP)).toEqual({ side: "right", left: 238, top: 52 });
  });

  it("puts the card below an entry of the open phone menu", () => {
    const spot = spotlightBox({ top: 300, left: 12, width: 351, height: 32 });
    expect(cardSpot(spot, PHONE_CARD, PHONE)).toEqual({ side: "below", left: 16, top: 350 });
  });

  it("puts the card above an entry near the bottom of a phone", () => {
    const spot = spotlightBox({ top: 700, left: 12, width: 351, height: 32 });
    expect(cardSpot(spot, PHONE_CARD, PHONE)).toEqual({ side: "above", left: 16, top: 514 });
  });

  it("gives up rather than cover a target that leaves no room", () => {
    expect(cardSpot({ top: 10, left: 10, width: 1260, height: 780 }, CARD, DESKTOP)).toBeNull();
  });

  it("never covers the element it describes", () => {
    const targets: Box[] = [
      { top: 20, left: 12, width: 36, height: 32 },
      { top: 760, left: 12, width: 208, height: 32 },
      { top: 300, left: 900, width: 360, height: 200 },
      { top: 40, left: 500, width: 600, height: 500 },
    ];
    for (const target of targets) {
      const spot = spotlightBox(target);
      const card = cardSpot(spot, CARD, DESKTOP);
      expect(card, JSON.stringify(target)).not.toBeNull();
      if (card) expect(overlaps(card, CARD, spot), JSON.stringify(target)).toBe(false);
    }
  });
});

describe("isOnScreen", () => {
  it("needs a size and at least part of the box inside the viewport", () => {
    expect(isOnScreen({ top: 10, left: 10, width: 0, height: 0 }, DESKTOP)).toBe(false);
    expect(isOnScreen({ top: -60, left: 10, width: 100, height: 40 }, DESKTOP)).toBe(false);
    expect(isOnScreen({ top: 790, left: 10, width: 100, height: 40 }, DESKTOP)).toBe(true);
  });
});
