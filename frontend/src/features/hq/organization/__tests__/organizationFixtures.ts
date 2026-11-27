import type { HqOrganization, HqOrganizationPage, HqPractice } from "@/lib/api/types";
import { LAKESIDE } from "../../practice/__tests__/practiceFixtures";

export const ACME: HqOrganization = {
  id: "o1",
  name: "Acme Health",
  status: "active",
  plan: "professional",
  renews_on: "2099-03-01",
  practices: 2,
  combined_practices: 1,
  admins: 1,
  providers: 3,
  created_on: "2026-11-01",
  closed_at: null,
  purge_after: null,
  purged_at: null,
  billing_provider: "stripe",
  billing_status: "active",
  billing_interval: "monthly",
};

export const ACME_PAGE: HqOrganizationPage = {
  organization: ACME,
  practices: [
    {
      id: "p1",
      name: "Lakeside Primary Care",
      status: "active",
      plan: "professional",
      renews_on: "2099-03-01",
      combined_billing: true,
      users: 4,
      providers: 3,
      open: true,
    },
    {
      id: "p2",
      name: "Harbor Pediatrics",
      status: "trial",
      plan: "trial",
      renews_on: null,
      combined_billing: false,
      users: 2,
      providers: 1,
      open: true,
    },
  ],
  admins: [{ id: "u1", name: "Dana Fox", email: "dana@acme.example.com", mfa_enabled: true, last_active_at: null }],
  plan: {
    plan: "professional",
    standing: "active",
    renews_on: "2099-03-01",
    ending_soon: false,
    providers: 3,
    practices: [
      { id: "p1", name: "Lakeside Primary Care", status: "active", providers: 3, provider_limit: 50, users: 4, user_limit: null },
    ],
    subscription: {
      provider: "stripe",
      interval: "monthly",
      status: "active",
      cancel_at_period_end: false,
      current_period_end: "2099-03-01",
      quantity: 3,
      managed_by: "portal",
    },
  },
};

export const UNATTACHED: HqPractice = { ...LAKESIDE, id: "p3", name: "Northside Clinic" };
export const ELSEWHERE: HqPractice = { ...LAKESIDE, id: "p4", name: "Bayview", organization_id: "o2", organization_name: "Bay Group" };
