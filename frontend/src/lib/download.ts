export function saveFile(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

const QUOTED_MARKS = ['"', ",", "\n"];

function csvCell(value: string | number | null): string {
  const text = value === null ? "" : String(value);
  const needsQuotes = QUOTED_MARKS.some((mark) => text.includes(mark));
  return needsQuotes ? `"${text.replaceAll('"', '""')}"` : text;
}

export function toCsv(header: string[], rows: (string | number | null)[][]): string {
  return [header, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
}
