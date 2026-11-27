export const ASSIGNED_TEXT = {
  title: "Assigned to you",
  tableLabel: "Blind coding assigned to you",
  empty: "Nothing assigned to you",
  purposes: { audit: "Blind audit", training: "Training set" },
  columns: { kind: "Kind", started: "Assigned", progress: "Coded", action: "Open" },
  progress: (done: number, total: number) => `${done} of ${total}`,
  code: "Code",
  finished: "Done",
  codeLabel: (kind: string, day: string) => `Code ${kind} assigned ${day}`,
} as const;
