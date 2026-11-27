"use client";

import { useId, type ReactNode } from "react";
import { Button } from "./Button";
import { useModalDialog } from "./useModalDialog";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  closeLabel: string;
  children: ReactNode;
}

export function Drawer({ open, onClose, title, closeLabel, children }: DrawerProps) {
  const ref = useModalDialog(open);
  const titleId = useId();

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      className="m-0 ml-auto h-dvh max-h-dvh w-full max-w-150 overflow-hidden bg-muted-panel p-0 text-label shadow-dialog backdrop:bg-scrim"
    >
      {open ? (
        <div className="flex h-full flex-col">
          <div className="flex flex-none items-center justify-between gap-3 border-b border-separator bg-surface px-5 py-3.5">
            <h2 id={titleId} className="m-0 text-title2 font-bold tracking-headline">
              {title}
            </h2>
            <Button variant="plain" onClick={onClose}>
              {closeLabel}
            </Button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
        </div>
      ) : null}
    </dialog>
  );
}
