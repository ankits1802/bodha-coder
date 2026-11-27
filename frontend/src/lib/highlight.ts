export type HighlightTone = "ok" | "warn" | "bad";

export interface Mark {
  quote: string;
  tone: HighlightTone;
}

export interface Segment {
  text: string;
  tone: HighlightTone | null;
}

interface Span {
  start: number;
  end: number;
}

interface Range extends Span {
  tone: HighlightTone;
}

interface FoldedText {
  text: string;
  starts: number[];
  ends: number[];
}

const WHITESPACE = /\s/;

function fold(text: string): FoldedText {
  let folded = "";
  const starts: number[] = [];
  const ends: number[] = [];
  let index = 0;
  for (const char of text) {
    const end = index + char.length;
    if (!WHITESPACE.test(char)) {
      const lower = char.toLowerCase();
      folded += lower;
      for (let unit = 0; unit < lower.length; unit += 1) {
        starts.push(index);
        ends.push(end);
      }
    } else if (folded.endsWith(" ")) {
      ends[ends.length - 1] = end;
    } else {
      folded += " ";
      starts.push(index);
      ends.push(end);
    }
    index = end;
  }
  return { text: folded, starts, ends };
}

function spansOf(note: FoldedText, quote: string): Span[] {
  const needle = fold(quote.trim()).text;
  if (!needle) return [];
  const found: Span[] = [];
  let from = note.text.indexOf(needle);
  while (from >= 0) {
    found.push({ start: note.starts[from] ?? 0, end: note.ends[from + needle.length - 1] ?? 0 });
    from = note.text.indexOf(needle, from + needle.length);
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

export function containsQuote(text: string, quote: string): boolean {
  return spansOf(fold(text), quote).length > 0;
}

export function highlightSegments(text: string, marks: Mark[]): Segment[] {
  const note = fold(text);
  const ranges = withoutOverlaps(marks.flatMap((mark) => spansOf(note, mark.quote).map((span) => ({ ...span, tone: mark.tone }))));
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
