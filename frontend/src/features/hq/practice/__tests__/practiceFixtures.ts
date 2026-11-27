import type { HqActivityPage, HqExpenditure, HqPerson, HqPractice, HqPracticePage } from "@/lib/api/types";

export const LAKESIDE: HqPractice = {
  id: "p1",
  name: "Lakeside Primary Care",
  status: "active",
  plan: "professional",
  seats: 10,
  users: 2,
  providers: 3,
  waiting: 4,
  renews_on: "2099-03-01",
  time_zone: "America/Chicago",
  source: "self",
  signed_up_on: "2026-11-02",
  failed_24h: 0,
  last_failure: null,
  admin_name: "Priya Raman",
  admin_email: "priya@lakeside.example.com",
  admin_status: "active",
  billing_provider: "stripe",
  billing_status: "active",
  billing_interval: "monthly",
  closed_at: null,
  purge_after: null,
  purged_at: null,
};

export const PAGE: HqPracticePage = {
  practice: LAKESIDE,
  places: [
    { code: "11", name: "Office", active: true, providers: 2, notes: 40 },
    { code: "31", name: "Skilled nursing facility", active: false, providers: 0, notes: 3 },
  ],
};

export const PEOPLE: HqPerson[] = [
  {
    id: "u1",
    name: "Priya Raman",
    email: "priya@lakeside.example.com",
    role: "admin",
    status: "active",
    mfa_enabled: true,
    last_active_at: null,
  },
  {
    id: "u2",
    name: "Tomas Reyes",
    email: "tomas@lakeside.example.com",
    role: "coder",
    status: "invited",
    mfa_enabled: false,
    last_active_at: null,
  },
];

const ZERO = {
  analyses: 0,
  notes: 0,
  input_tokens: 0,
  output_tokens: 0,
  cost_usd: 0,
  cost_per_note_usd: null,
  unpriced_analyses: 0,
};

export const QUIET_SPEND: HqExpenditure = {
  from: "2026-11-01",
  to: "2026-11-28",
  time_zone: "UTC",
  totals: ZERO,
  practices: [{ id: "p1", name: "Lakeside Primary Care", plan: "professional", plan_monthly_cents: 24_900, ...ZERO, providers: [] }],
  unpriced_models: [],
};

export const ACTIVITY: HqActivityPage = {
  items: [{ at: "2026-11-20T15:00:00Z", actor: "Bodha Admin", action: "practice renewed", practice_id: "p1", detail: "renews 2099-03-01", changes: null }],
  total: 1,
  offset: 0,
  page_size: 100,
  actions: ["practice renewed"],
};
