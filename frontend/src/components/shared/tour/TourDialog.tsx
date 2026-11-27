"use client";

import { useId, useRef, useState, type KeyboardEvent } from "react";
import type { TourOutcome } from "@/lib/api/types";
import { TOUR_TEXT } from "./strings";
import { TourCard, type CardActions, type CardPlace } from "./TourCard";
import { focusWrapTarget, moveFor } from "./tourKeys";
import { TourSpotlight } from "./TourSpotlight";
import type { TourStep } from "./tourSteps";
import { useCardSpot } from "./useCardSpot";
import { useFocusKept, useTourModal } from "./useTourModal";
import { useTourPage } from "./useTourPage";
import { useTourTarget } from "./useTourTarget";

interface TourDialogProps {
  steps: readonly [TourStep, ...TourStep[]];
  onMenu: (open: boolean) => void;
  onClose: (outcome: TourOutcome) => void;
}

const DIALOG =
  "fixed inset-0 z-50 m-0 h-full max-h-none w-full max-w-none overflow-hidden border-0 bg-transparent p-0 text-label backdrop:bg-transparent";

function placeOf(index: number, total: number): CardPlace {
  if (index === total - 1) return "last";
  return index === 0 ? "first" : "middle";
}

function announcement(step: TourStep, count: string, highlighted: boolean): string {
  const say = highlighted ? TOUR_TEXT.announceHighlighted : TOUR_TEXT.announce;
  return say(count, step.title, step.line);
}

export function TourDialog({ steps, onMenu, onClose }: TourDialogProps) {
  const [index, setIndex] = useState(0);
  const [moved, setMoved] = useState(false);
  const step = steps[index] ?? steps[0];
  const dialog = useRef<HTMLDialogElement>(null);
  const card = useRef<HTMLDivElement>(null);
  const primary = useRef<HTMLButtonElement>(null);
  const closed = useRef(false);
  const ids = { title: useId(), line: useId() };
  const target = useTourTarget(step.target);
  const placement = useCardSpot(target, card);
  const leave = useTourPage(step.path, onMenu);
  useTourModal(dialog, primary);
  useFocusKept(card, primary, index);

  const count = TOUR_TEXT.count(index + 1, steps.length);
  const settling = target.status === "searching";

  function close(outcome: TourOutcome): void {
    if (closed.current) return;
    closed.current = true;
    leave();
    onClose(outcome);
  }

  function go(delta: number): void {
    setMoved(true);
    setIndex((current) => Math.min(Math.max(current + delta, 0), steps.length - 1));
  }

  const actions: CardActions = {
    next: () => (index === steps.length - 1 ? close("completed") : go(1)),
    back: () => go(-1),
    skip: () => close("skipped"),
  };

  function wrapFocus(event: KeyboardEvent<HTMLDialogElement>): void {
    const controls = Array.from(card.current?.querySelectorAll<HTMLElement>("button:not(:disabled)") ?? []);
    const next = focusWrapTarget(controls, document.activeElement, event.shiftKey);
    if (!next) return;
    event.preventDefault();
    next.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLDialogElement>): void {
    if (event.key === "Tab") return wrapFocus(event);
    const move = moveFor(event.key, event.target instanceof HTMLButtonElement);
    if (move === null) return;
    event.preventDefault();
    if (!event.repeat) actions[move]();
  }

  return (
    <dialog
      ref={dialog}
      aria-labelledby={ids.title}
      aria-describedby={step.line ? ids.line : undefined}
      onKeyDown={onKeyDown}
      onCancel={(event) => {
        event.preventDefault();
        actions.skip();
      }}
      onClose={() => {
        if (!dialog.current?.open) actions.skip();
      }}
      className={DIALOG}
    >
      <TourSpotlight box={placement.spotlight} />
      <TourCard
        text={{ title: step.title, line: step.line, count }}
        ids={ids}
        place={placeOf(index, steps.length)}
        spot={placement.card}
        settling={settling}
        actions={actions}
        cardRef={card}
        primaryRef={primary}
      />
      <p aria-live="polite" className="sr-only">
        {moved && !settling ? announcement(step, count, placement.spotlight !== null) : ""}
      </p>
    </dialog>
  );
}
