"use client";

import { useSyncExternalStore } from "react";

export interface ToastAction {
  label: string;
  run: () => void;
}

export interface Toast {
  id: number;
  message: string;
  action: ToastAction | null;
}

export const TOAST_SECONDS = 8;

let current: Toast | null = null;
let counter = 0;
const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function showToast(message: string, action: ToastAction | null = null): void {
  counter += 1;
  current = { id: counter, message, action };
  emit();
}

export function dismissToast(id?: number): void {
  if (current === null || (id !== undefined && current.id !== id)) return;
  current = null;
  emit();
}

export function runToastAction(): boolean {
  const action = current?.action;
  if (!action) return false;
  dismissToast();
  action.run();
  return true;
}

export function currentToast(): Toast | null {
  return current;
}

export function useToast(): Toast | null {
  return useSyncExternalStore(
    subscribe,
    () => current,
    () => null,
  );
}
