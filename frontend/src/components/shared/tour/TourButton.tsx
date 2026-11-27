"use client";

import { Button } from "@/components/ui/Button";
import type { User } from "@/lib/api/types";
import { entryClasses } from "../sidebar/NavEntry";
import { startTour } from "./startTour";
import { TOUR_TEXT } from "./strings";
import { REPLAY_TARGET } from "./tourSteps";

const STROKE = { fill: "none", stroke: "currentColor", strokeWidth: 1.3, strokeLinecap: "round", strokeLinejoin: "round" } as const;

function CompassIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="flex-none text-secondary">
      <circle cx="8" cy="8" r="6" {...STROKE} />
      <path d="M10.4 5.6 9.1 9.1 5.6 10.4 6.9 6.9z" {...STROKE} />
    </svg>
  );
}

export function TourButton({ user, collapsed }: { user: User; collapsed: boolean }) {
  if (user.billing_only) return null;
  if (collapsed) {
    return (
      <button
        type="button"
        onClick={startTour}
        title={TOUR_TEXT.take}
        data-tour={REPLAY_TARGET}
        className={`cursor-pointer ${entryClasses(true, false)}`}
      >
        <CompassIcon />
        <span className="sr-only">{TOUR_TEXT.take}</span>
      </button>
    );
  }
  return (
    <Button variant="plain" size="sm" className="self-start" data-tour={REPLAY_TARGET} onClick={startTour}>
      {TOUR_TEXT.take}
    </Button>
  );
}
