export const PAD_WIDTH = 500;
export const PAD_HEIGHT = 200;
export const STROKE_WIDTH = 2.6;
export const MIN_INK_LENGTH = 24;

export type PadPointer = "pen" | "mouse" | "touch";

export interface PadPoint {
  x: number;
  y: number;
}

export interface PadStroke {
  pointer: PadPointer;
  points: PadPoint[];
}

export interface PadBounds {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

interface PadRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

const clamp = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value));

export function padPointer(kind: string | undefined): PadPointer {
  return kind === "pen" || kind === "touch" ? kind : "mouse";
}

export function toPadPoint(clientX: number, clientY: number, rect: PadRect): PadPoint {
  if (rect.width <= 0 || rect.height <= 0) return { x: 0, y: 0 };
  return {
    x: clamp(((clientX - rect.left) * PAD_WIDTH) / rect.width, 0, PAD_WIDTH),
    y: clamp(((clientY - rect.top) * PAD_HEIGHT) / rect.height, 0, PAD_HEIGHT),
  };
}

export function inkLength(strokes: readonly PadStroke[]): number {
  let total = 0;
  for (const stroke of strokes) {
    for (let index = 1; index < stroke.points.length; index += 1) {
      const from = stroke.points[index - 1];
      const to = stroke.points[index];
      if (from && to) total += Math.hypot(to.x - from.x, to.y - from.y);
    }
  }
  return total;
}

export function hasInk(strokes: readonly PadStroke[]): boolean {
  return inkLength(strokes) >= MIN_INK_LENGTH;
}

export function strokeBounds(strokes: readonly PadStroke[]): PadBounds | null {
  const points = strokes.flatMap((stroke) => stroke.points);
  if (points.length === 0) return null;
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  return { left: Math.min(...xs), top: Math.min(...ys), right: Math.max(...xs), bottom: Math.max(...ys) };
}

export function drawStrokes(context: CanvasRenderingContext2D, strokes: readonly PadStroke[], ink: string): void {
  context.lineCap = "round";
  context.lineJoin = "round";
  context.lineWidth = STROKE_WIDTH;
  context.strokeStyle = ink;
  for (const stroke of strokes) {
    const [first, ...rest] = stroke.points;
    if (!first) continue;
    context.beginPath();
    context.moveTo(first.x, first.y);
    for (const point of rest.length > 0 ? rest : [{ x: first.x + 0.1, y: first.y }]) context.lineTo(point.x, point.y);
    context.stroke();
  }
}
