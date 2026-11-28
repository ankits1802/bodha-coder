"use client";

import { useLayoutEffect, useRef, type RefObject } from "react";

function show(dialog: HTMLDialogElement): void {
  if (dialog.open) return;
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function hide(dialog: HTMLDialogElement): void {
  if (!dialog.open) return;
  if (typeof dialog.close === "function") dialog.close();
  else dialog.removeAttribute("open");
}

function isFocusLost(dialog: HTMLDialogElement): boolean {
  const active = document.activeElement;
  return active === null || active === document.body || dialog.contains(active);
}

export function useModalDialog(open: boolean): RefObject<HTMLDialogElement | null> {
  const ref = useRef<HTMLDialogElement>(null);

  useLayoutEffect(() => {
    const dialog = ref.current;
    if (!dialog || !open) return;
    const opener = document.activeElement instanceof HTMLElement && document.activeElement !== document.body ? document.activeElement : null;
    show(dialog);
    return () => {
      const focusWasInside = isFocusLost(dialog);
      hide(dialog);
      if (opener?.isConnected && (focusWasInside || isFocusLost(dialog))) opener.focus();
    };
  }, [open]);

  return ref;
}
