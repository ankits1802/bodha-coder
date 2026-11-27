import type { QueuePage, QueueRow, User } from "@/lib/api/types";

export const CODER: User = {
  id: "user-1",
  name: "Priya Nair",
  email: "priya.nair@example.com",
  role: "coder",
  billing_only: false,
  practice: {
    id: "practice-1",
    name: "Lakeside Primary Care",
    checks: { em: true, icd: true, cdi: true, audit: true, mips: false, hcc: false },
    idle_minutes: 15,
    time_zone: "America/Chicago",
  },
};

const LANES: QueuePage["lanes"] = {
  approve: { total: 3, due_soon: 1 },
  coder: { total: 4, due_soon: 2 },
  provider: { total: 1, due_soon: 0 },
  compliance: { total: 2, due_soon: 0 },
};

export const ROW: QueueRow = {
  id: "note-1",
  patient_name: "Marisol Reyes",
  provider_name: "Elena Varga",
  service_date: "2026-11-25",
  status: "ready",
  lane: "coder",
  lane_reason: "code_changes",
  headline: "Billed too high",
  place_code: "11",
  visit_type: "Established patient",
  flag_reason: null,
  flagged_by: null,
  due_at: "2026-11-27T18:00:00Z",
  file_name: "2026-11-25 - REYES MARISOL - 99215.pdf",
  assigned_to: null,
  payer: null,
  assignee_name: null,
  billed: ["99215", "I10"],
  suggested: ["99214"],
  em_action: "lower",
};

export function page(items: QueueRow[], failed = 0): QueuePage {
  return { items, lanes: LANES, total: 10, all_total: 12, failed, page_size: 50 };
}
