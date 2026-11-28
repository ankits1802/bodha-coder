"use client";

import { useEffect, useRef, type PointerEvent } from "react";
import { Button } from "@/components/ui/Button";
import { cssToken } from "./signatureImage";
import { SIGNATURE_TEXT } from "./strings";
import { drawStrokes, PAD_HEIGHT, PAD_WIDTH, padPointer, toPadPoint, type PadStroke } from "./strokes";

interface SignaturePadProps {
  strokes: PadStroke[];
  disabled?: boolean;
  onChange: (strokes: PadStroke[]) => void;
}

interface ActiveStroke {
  pointerId: number;
  stroke: PadStroke;
  rect: DOMRect;
}

function paint(canvas: HTMLCanvasElement, strokes: readonly PadStroke[]): void {
  const context = canvas.getContext("2d");
  if (!context) return;
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.round(rect.width * ratio));
  canvas.height = Math.max(1, Math.round(rect.height * ratio));
  context.setTransform(canvas.width / PAD_WIDTH, 0, 0, canvas.height / PAD_HEIGHT, 0, 0);
  context.clearRect(0, 0, PAD_WIDTH, PAD_HEIGHT);
  drawStrokes(context, strokes, cssToken("--color-ink", "black"));
}

export function SignaturePad({ strokes, disabled = false, onChange }: SignaturePadProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const active = useRef<ActiveStroke | null>(null);
  const empty = strokes.length === 0;

  useEffect(() => {
    if (canvas.current) paint(canvas.current, strokes);
  }, [strokes]);

  function add(point: { clientX: number; clientY: number }): void {
    const current = active.current;
    if (!current) return;
    current.stroke.points.push(toPadPoint(point.clientX, point.clientY, current.rect));
    if (canvas.current) paint(canvas.current, [...strokes, current.stroke]);
  }

  function start(event: PointerEvent<HTMLCanvasElement>): void {
    if (disabled || active.current || (event.pointerType === "mouse" && event.button !== 0)) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    const stroke: PadStroke = { pointer: padPointer(event.pointerType), points: [] };
    active.current = { pointerId: event.pointerId, stroke, rect: event.currentTarget.getBoundingClientRect() };
    add(event);
  }

  function move(event: PointerEvent<HTMLCanvasElement>): void {
    if (active.current?.pointerId === event.pointerId) add(event);
  }

  function end(event: PointerEvent<HTMLCanvasElement>): void {
    const current = active.current;
    if (!current || current.pointerId !== event.pointerId) return;
    active.current = null;
    if (current.stroke.points.length > 0) onChange([...strokes, current.stroke]);
  }

  return (
    <div className="flex flex-col gap-2">
      <canvas
        ref={canvas}
        role="img"
        aria-label={empty ? SIGNATURE_TEXT.padEmpty : SIGNATURE_TEXT.padSigned}
        className="block aspect-[5/2] w-full cursor-crosshair touch-none rounded-field border border-separator bg-paper select-none"
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={end}
        onPointerCancel={end}
        onLostPointerCapture={end}
      />
      <div className="flex justify-end gap-1">
        <Button variant="plain" size="sm" disabled={disabled || empty} onClick={() => onChange(strokes.slice(0, -1))}>
          {SIGNATURE_TEXT.undo}
        </Button>
        <Button variant="plain" size="sm" disabled={disabled || empty} onClick={() => onChange([])}>
          {SIGNATURE_TEXT.clear}
        </Button>
      </div>
    </div>
  );
}
