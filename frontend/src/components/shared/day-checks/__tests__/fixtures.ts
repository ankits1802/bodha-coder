import type { DayNote, ProviderDay } from "@/lib/api/types";

function note(id: string, patient: string, code: string, minutes: number): DayNote {
  return { id, patient_name: patient, status: "ready", lane: "coder", em_code: code, minutes };
}

export const BUSY_DAY: ProviderDay = {
  provider: { id: "p1", name: "Elena Varga" },
  service_date: "2026-11-25",
  notes: [note("a", "Ana Diaz", "99215", 600), note("b", "Ben Cole", "99215", 300), note("c", "Cara Lim", "99213", 100)],
  total_minutes: 1000,
  timed_notes: 3,
  visits: 3,
  levels: [
    { code: "99213", count: 1 },
    { code: "99215", count: 2 },
  ],
  high_level_visits: 2,
  high_level_share: 0.8,
  compared: 3,
  duplicates: [{ first: "a", second: "b", similarity: 1 }],
  flags: ["time_over_day", "cloned_text", "high_level_share"],
};

export const QUIET_DAY: ProviderDay = {
  ...BUSY_DAY,
  provider: { id: "p2", name: "Omar Haddad" },
  service_date: "2026-11-24",
  notes: [note("d", "Dev Rao", "99213", 20), note("e", "Eva Moss", "99212", 15)],
  total_minutes: 35,
  timed_notes: 2,
  visits: 2,
  high_level_visits: 0,
  high_level_share: 0,
  duplicates: [],
  flags: [],
};
