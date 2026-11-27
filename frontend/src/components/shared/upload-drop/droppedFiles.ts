"use client";

import { useEffect, useEffectEvent } from "react";

type Receiver = (files: File[]) => void;

const PDF_TYPE = "application/pdf";
const PDF_SUFFIX = ".pdf";

let pending: File[] = [];
let receiver: Receiver | null = null;

export function isPdf(file: File): boolean {
  return file.type === PDF_TYPE || file.name.toLowerCase().endsWith(PDF_SUFFIX);
}

export function handOffFiles(files: File[]): void {
  if (files.length === 0) return;
  if (receiver) receiver(files);
  else pending = [...pending, ...files];
}

export function takeDroppedFiles(): File[] {
  const taken = pending;
  pending = [];
  return taken;
}

export function receiveDroppedFiles(next: Receiver): () => void {
  receiver = next;
  const waiting = takeDroppedFiles();
  if (waiting.length > 0) queueMicrotask(() => next(waiting));
  return () => {
    if (receiver === next) receiver = null;
  };
}

export function useDroppedFiles(onFiles: Receiver): void {
  const deliver = useEffectEvent(onFiles);
  useEffect(() => receiveDroppedFiles((files) => deliver(files)), []);
}
