import { CODER } from "@/features/queue/__tests__/fixtures";
import type {
  MyOrganizationPractice,
  OrganizationInsights,
  OrganizationOverview,
  OrganizationPlan,
  PracticeInsight,
  User,
} from "@/lib/api/types";

export const ORGANIZATION_ID = "org-1";

export const ORGANIZATION_ADMIN: User = {
  ...CODER,
  role: "admin",
  organizations: [{ id: ORGANIZATION_ID, name: "Acme Health", role: "admin" }],
};

export function practiceRow(changes: Partial<MyOrganizationPractice> = {}): MyOrganizationPractice {
  return {
    id: "practice-3",
    name: "Lakeside East",
    status: "active",
    plan: "professional",
    renews_on: "2027-01-15",
    combined_billing: true,
    users: 4,
    providers: 3,
    open: true,
    my_role: "admin",
    ...changes,
  };
}

export const OVERVIEW: OrganizationOverview = {
  id: ORGANIZATION_ID,
  name: "Acme Health",
  plan: "professional",
  renews_on: "2027-01-15",
  practices: [
    practiceRow(),
    practiceRow({ id: "practice-2", name: "Riverbend Clinic", combined_billing: false, my_role: null, users: 2, providers: 1 }),
  ],
  admins: [{ id: CODER.id, name: CODER.name, email: CODER.email }],
};

export function organizationPlan(changes: Partial<OrganizationPlan> = {}): OrganizationPlan {
  return {
    plan: "trial",
    standing: "trial",
    renews_on: "2026-12-12",
    ending_soon: false,
    providers: 4,
    practices: [
      { id: "practice-1", name: "Lakeside Primary Care", status: "trial", providers: 3, provider_limit: 50, users: 4, user_limit: null },
    ],
    subscription: null,
    ...changes,
  };
}

const OUTCOMES = { matched: 10, billed_too_low: 2, billed_too_high: 3, diagnosis_changes: 4 };

function insight(changes: Partial<PracticeInsight>): PracticeInsight {
  return {
    id: "practice-1",
    name: "Lakeside Primary Care",
    notes: 40,
    approved: 20,
    approved_on_time: 10,
    estimated_notes: 12,
    outcomes: OUTCOMES,
    difference: 125.5,
    ...changes,
  };
}

export const INSIGHTS: OrganizationInsights = {
  days: 30,
  totals: {
    notes: 52,
    approved: 25,
    approved_on_time: 15,
    estimated_notes: 15,
    outcomes: { matched: 14, billed_too_low: 3, billed_too_high: 4, diagnosis_changes: 5 },
    difference: 150.5,
  },
  practices: [insight({}), insight({ id: "practice-2", name: "Riverbend Clinic", notes: 12, approved: 5, approved_on_time: 5, difference: 25 })],
};
