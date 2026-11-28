import { UserFacingError } from "@/lib/api/errors";
import type { SignatureDraftBody, SignatureSource } from "@/lib/api/types";
import { SIGNATURE_TEXT } from "./strings";
import { drawStrokes, strokeBounds, type PadStroke } from "./strokes";

export interface SignatureEntry {
  mode: SignatureSource;
  name: string;
  strokes: PadStroke[];
  upload: string | null;
}

const EXPORT_SCALE = 3;
const MARGIN = 8;
const MIN_SIDE = 32;
const MAX_SIDE = 1200;
const TYPED_SIZE = 72;
const MAX_IMAGE_BYTES = 1_400_000;
const PNG = "image/png";

export function cssToken(name: string, fallback: string): string {
  if (typeof document === "undefined") return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

function paper(width: number, height: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(MIN_SIDE, Math.round(width));
  canvas.height = Math.max(MIN_SIDE, Math.round(height));
  const context = canvas.getContext("2d");
  if (!context) throw new UserFacingError(SIGNATURE_TEXT.noCanvas);
  context.fillStyle = cssToken("--color-paper", "white");
  context.fillRect(0, 0, canvas.width, canvas.height);
  return [canvas, context];
}

function dataUrlBytes(url: string): number {
  return Math.floor(((url.length - url.indexOf(",") - 1) * 3) / 4);
}

function checkedSize(url: string): string {
  if (dataUrlBytes(url) > MAX_IMAGE_BYTES) throw new UserFacingError(SIGNATURE_TEXT.tooLarge);
  return url;
}

export function drawnImage(strokes: readonly PadStroke[]): string | null {
  const bounds = strokeBounds(strokes);
  if (!bounds) return null;
  const width = bounds.right - bounds.left + MARGIN * 2;
  const height = bounds.bottom - bounds.top + MARGIN * 2;
  const scale = Math.min(EXPORT_SCALE, MAX_SIDE / Math.max(width, height));
  const [canvas, context] = paper(width * scale, height * scale);
  context.setTransform(scale, 0, 0, scale, (MARGIN - bounds.left) * scale, (MARGIN - bounds.top) * scale);
  drawStrokes(context, strokes, cssToken("--color-ink", "black"));
  return checkedSize(canvas.toDataURL(PNG));
}

export function typedImage(name: string): string | null {
  const text = name.trim();
  if (!text) return null;
  const font = `${TYPED_SIZE}px ${cssToken("--font-signature", "cursive")}`;
  const [, probe] = paper(1, 1);
  probe.font = font;
  const width = Math.min(MAX_SIDE, Math.ceil(probe.measureText(text).width) + TYPED_SIZE);
  const height = TYPED_SIZE * 1.8;
  const [canvas, context] = paper(width, height);
  context.font = font;
  context.fillStyle = cssToken("--color-ink", "black");
  context.textBaseline = "middle";
  context.fillText(text, TYPED_SIZE / 2, height / 2, width - TYPED_SIZE);
  return checkedSize(canvas.toDataURL(PNG));
}

function readFile(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new UserFacingError(SIGNATURE_TEXT.unreadable));
    reader.readAsDataURL(file);
  });
}

function loadImage(source: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new UserFacingError(SIGNATURE_TEXT.unreadable));
    image.src = source;
  });
}

export async function uploadedImage(file: Blob): Promise<string> {
  const image = await loadImage(await readFile(file));
  const scale = Math.min(1, MAX_SIDE / Math.max(image.naturalWidth, image.naturalHeight, 1));
  const [canvas, context] = paper(image.naturalWidth * scale, image.naturalHeight * scale);
  context.drawImage(image, 0, 0, canvas.width, canvas.height);
  return checkedSize(canvas.toDataURL(PNG));
}

export async function draftFrom(entry: SignatureEntry): Promise<SignatureDraftBody> {
  const image = entry.mode === "drawn" ? drawnImage(entry.strokes) : entry.mode === "typed" ? typedImage(entry.name) : entry.upload;
  if (!image) throw new UserFacingError(SIGNATURE_TEXT.empty);
  return { source: entry.mode, typed_name: entry.name.trim(), image };
}
