"use client";

import { useEffect, type RefObject } from "react";

type DialogRef = RefObject<HTMLDialogElement | null>;
type ElementRef<T extends HTMLElement> = RefObject<T | null>;

function show(dialog: HTMLDialogElement): void {
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function hide(dialog: HTMLDialogElement): void {
  if (typeof dialog.close === "function") dialog.close();
  else dialog.removeAttribute("open");
}

export function useTourModal(dialog: DialogRef, primary: ElementRef<HTMLButtonElement>): void {
  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    show(node);
    primary.current?.focus();
    return () => {
      hide(node);
      opener?.focus();
    };
  }, [dialog, primary]);
}

export function useFocusKept(card: ElementRef<HTMLDivElement>, primary: ElementRef<HTMLButtonElement>, step: number): void {
  useEffect(() => {
    if (!card.current?.contains(document.activeElement)) primary.current?.focus();
  }, [card, primary, step]);
}
