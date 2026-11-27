"use client";

import { useId, type ReactNode } from "react";
import { useModalDialog } from "./useModalDialog";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  description?: ReactNode;
  footer?: ReactNode;
  size?: "md" | "lg";
  children: ReactNode;
}

const SIZES = { md: "max-w-120", lg: "max-w-170" } as const;

export function Dialog({ open, onClose, title, description, footer, size = "md", children }: DialogProps) {
  const ref = useModalDialog(open);
  const titleId = useId();

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      className={`m-auto w-[calc(100%-2rem)] ${SIZES[size]} overflow-hidden rounded-float bg-muted-panel p-0 text-label shadow-dialog backdrop:bg-scrim`}
    >
      {open ? (
        <>
          <div className="px-7 pt-6 pb-2">
            <h2 id={titleId} className="m-0 text-title2 font-bold tracking-headline">
              {title}
            </h2>
            {description ? <p className="mt-0.5 text-secondary">{description}</p> : null}
          </div>
          <div className="flex flex-col gap-5.5 px-7 pt-4 pb-6">{children}</div>
          {footer ? (
            <div className="flex flex-wrap items-center justify-end gap-2 border-t border-separator bg-surface px-5 py-3.5">
              {footer}
            </div>
          ) : null}
        </>
      ) : null}
    </dialog>
  );
}
