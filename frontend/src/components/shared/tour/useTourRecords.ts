"use client";

import { useCallback, useEffect } from "react";
import { useRemote } from "@/hooks/useRemote";
import { messageOf } from "@/lib/api/errors";
import { getTours, saveTour } from "@/lib/api/tours";
import type { TourKey, TourOutcome, TourRecord, User } from "@/lib/api/types";
import { openOverlay } from "../overlays";
import { showToast } from "../toast/toastStore";
import { TOUR_VERSION, isTourDue, tourKeyFor } from "./tourSteps";

export const TOURS_KEY = "account-tours";
const TOURS_SECONDS = 3600;

function recordOf(tour: TourKey, outcome: TourOutcome): TourRecord {
  const now = new Date().toISOString();
  return {
    tour,
    version: TOUR_VERSION,
    completed_at: outcome === "completed" ? now : null,
    skipped_at: outcome === "skipped" ? now : null,
  };
}

export function useTourRecords(user: User): (outcome: TourOutcome) => void {
  const tour = tourKeyFor(user);
  const { state, replace } = useRemote(user.billing_only ? null : TOURS_KEY, getTours, TOURS_SECONDS);
  const records = state.status === "success" ? state.data : null;
  const due = records !== null && isTourDue(records, tour);

  useEffect(() => {
    if (due) openOverlay("tour");
  }, [due]);

  return useCallback(
    (outcome: TourOutcome) => {
      if (records !== null && !due) return;
      replace([...(records ?? []), recordOf(tour, outcome)]);
      saveTour(tour, { version: TOUR_VERSION, outcome }).catch((error: unknown) => showToast(messageOf(error)));
    },
    [records, due, tour, replace],
  );
}
