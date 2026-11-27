"use client";

import type { User } from "@/lib/api/types";
import { closeOverlay, useOpenOverlay } from "../overlays";
import { TourDialog } from "./TourDialog";
import { tourStepsFor } from "./tourSteps";
import { useTourRecords } from "./useTourRecords";

interface TourHostProps {
  user: User;
  onMenu: (open: boolean) => void;
}

export function TourHost({ user, onMenu }: TourHostProps) {
  const open = useOpenOverlay() === "tour";
  const record = useTourRecords(user);
  if (!open) return null;
  return (
    <TourDialog
      steps={tourStepsFor(user)}
      onMenu={onMenu}
      onClose={(outcome) => {
        closeOverlay();
        record(outcome);
      }}
    />
  );
}
