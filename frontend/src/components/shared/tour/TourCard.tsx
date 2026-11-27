import type { CSSProperties, Ref } from "react";
import { Button } from "@/components/ui/Button";
import { buttonClasses } from "@/components/ui/buttonStyles";
import { TOUR_TEXT } from "./strings";
import type { CardSpot } from "./tourPlacement";

export type CardPlace = "first" | "middle" | "last";

export interface CardText {
  title: string;
  line: string;
  count: string;
}

export interface CardActions {
  next: () => void;
  back: () => void;
  skip: () => void;
}

interface TourCardProps {
  text: CardText;
  ids: { title: string; line: string };
  place: CardPlace;
  spot: CardSpot | null;
  settling: boolean;
  actions: CardActions;
  cardRef: Ref<HTMLDivElement>;
  primaryRef: Ref<HTMLButtonElement>;
}

const SHAPE = "fixed flex w-[min(20rem,calc(100vw-2rem))] flex-col gap-3 rounded-panel bg-surface p-4.5 text-label shadow-dialog";
const PLACED = "top-0 left-0 motion-safe:transition-transform motion-safe:duration-200 motion-safe:ease-out";
const CENTRED = "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2";

function positionOf(spot: CardSpot | null): CSSProperties | undefined {
  return spot ? { transform: `translate(${spot.left}px, ${spot.top}px)` } : undefined;
}

export function TourCard({ text, ids, place, spot, settling, actions, cardRef, primaryRef }: TourCardProps) {
  return (
    <div
      ref={cardRef}
      data-side={spot?.side ?? "centre"}
      style={positionOf(spot)}
      className={`${SHAPE} ${spot ? PLACED : CENTRED} ${settling ? "opacity-0" : "opacity-100"}`}
    >
      <p className="m-0 text-footnote text-secondary tabular-nums">{text.count}</p>
      <div className="flex flex-col gap-1">
        <h2 id={ids.title} className="m-0 text-headline font-semibold tracking-headline">
          {text.title}
        </h2>
        {text.line ? (
          <p id={ids.line} className="m-0 text-body text-label-soft">
            {text.line}
          </p>
        ) : null}
      </div>
      <div className="flex items-center justify-between gap-2 pt-1">
        {place === "last" ? (
          <span />
        ) : (
          <Button variant="plain" size="sm" className="-ml-3" onClick={actions.skip}>
            {TOUR_TEXT.skip}
          </Button>
        )}
        <div className="flex gap-2">
          {place === "first" ? null : (
            <Button size="sm" onClick={actions.back}>
              {TOUR_TEXT.back}
            </Button>
          )}
          <button ref={primaryRef} type="button" onClick={actions.next} className={buttonClasses("primary", "sm")}>
            {place === "last" ? TOUR_TEXT.done : TOUR_TEXT.next}
          </button>
        </div>
      </div>
    </div>
  );
}
