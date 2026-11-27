import { describe, expect, it } from "vitest";
import type { HqPractice } from "@/lib/api/types";
import { editDraftFrom, practiceChanges } from "../practiceForm";

const PRACTICE: HqPractice = {
  id: "p1",
  name: "Lakeside Primary Care",
  status: "active",
  plan: "enterprise",
  seats: 30,
  users: 24,
  providers: 168,
  waiting: 288,
  renews_on: "2027-03-01",
  time_zone: "America/Chicago",
  source: "hq",
  signed_up_on: "2026-01-05",
  failed_24h: 0,
  last_failure: null,
  admin_name: "Priya Raman",
  admin_email: "priya@lakeside.example.com",
  admin_status: "active",
  billing_provider: null,
  billing_status: null,
  billing_interval: null,
};

describe("practiceChanges", () => {
  it("sends nothing when nothing changed", () => {
    expect(practiceChanges(PRACTICE, editDraftFrom(PRACTICE))).toEqual({});
  });

  it("sends only the fields that changed", () => {
    const draft = { ...editDraftFrom(PRACTICE), seats: "35", time_zone: "America/New_York" };
    expect(practiceChanges(PRACTICE, draft)).toEqual({ seats: 35, time_zone: "America/New_York" });
  });

  it("clears the renewal date with null", () => {
    expect(practiceChanges(PRACTICE, { ...editDraftFrom(PRACTICE), renews_on: "" })).toEqual({ renews_on: null });
    expect(practiceChanges(PRACTICE, { ...editDraftFrom(PRACTICE), name: "  Lakeside Family Care " })).toEqual({
      name: "Lakeside Family Care",
    });
  });
});
