export type HighlightTone = "ok" | "warn" | "bad";

export interface Mark {
  quote: string;
  tone: HighlightTone;
}

export interface Segment {
  text: string;
  tone: HighlightTone | null;
}

interface Range {
  start: number;
  end: number;
  tone: HighlightTone;
}

function rangesOf(text: string, mark: Mark): Range[] {
  const quote = mark.quote.trim();
  if (!quote) return [];
  const found: Range[] = [];
  let from = text.indexOf(quote);
  while (from >= 0) {
    found.push({ start: from, end: from + quote.length, tone: mark.tone });
    from = text.indexOf(quote, from + quote.length);
  }
  return found;
}

function withoutOverlaps(ranges: Range[]): Range[] {
  const ordered = [...ranges].sort((a, b) => a.start - b.start || b.end - a.end);
  const kept: Range[] = [];
  for (const range of ordered) {
    const last = kept[kept.length - 1];
    if (!last || range.start >= last.end) kept.push(range);
  }
  return kept;
}

export function highlightSegments(text: string, marks: Mark[]): Segment[] {
  const ranges = withoutOverlaps(marks.flatMap((mark) => rangesOf(text, mark)));
  const segments: Segment[] = [];
  let cursor = 0;
  for (const range of ranges) {
    if (range.start > cursor) segments.push({ text: text.slice(cursor, range.start), tone: null });
    segments.push({ text: text.slice(range.start, range.end), tone: range.tone });
    cursor = range.end;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), tone: null });
  return segments;
}
