export const SEARCH_TEXT = {
  title: "Search notes",
  label: "Search",
  placeholder: "Patient, provider, file or code",
  results: "Notes found",
  searching: "Searching",
  empty: "No notes found",
  retry: "Try again",
  meta: (provider: string, day: string) => `${provider} · seen ${day}`,
  firstResults: (count: string) => `First ${count} notes`,
  close: "Close",
} as const;
