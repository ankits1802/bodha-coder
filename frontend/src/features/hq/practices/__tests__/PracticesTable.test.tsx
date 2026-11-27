import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { HqPractice } from "@/lib/api/types";
import { PracticesTable } from "../PracticesTable";

const BASE: HqPractice = {
  id: "p1",
  name: "Northside Clinic",
  status: "active",
  plan: "professional",
  seats: 10,
  users: 4,
  providers: 6,
  waiting: 0,
  renews_on: "2027-03-01",
  time_zone: "America/Chicago",
  source: "hq",
  signed_up_on: "2026-01-05",
  failed_24h: 0,
  last_failure: null,
  admin_name: "Priya Raman",
  admin_email: "priya@northside.example.com",
  admin_status: "active",
};

const SELF: HqPractice = { ...BASE, id: "p2", name: "Harbor Pediatrics", status: "trial", plan: "trial", source: "self", signed_up_on: "2026-11-27" };

describe("PracticesTable", () => {
  it("marks a practice that signed itself up with a dot, the words and the day", () => {
    render(<PracticesTable practices={[BASE, SELF]} onEdit={vi.fn()} onAction={vi.fn()} />);
    const harbor = screen.getByText("Harbor Pediatrics").closest("tr");
    const northside = screen.getByText("Northside Clinic").closest("tr");
    if (!harbor || !northside) throw new Error("rows not rendered");
    expect(within(harbor).getByText("Self sign-up")).toBeInTheDocument();
    expect(within(harbor).getByText("27 Nov 2026")).toBeInTheDocument();
    expect(within(northside).queryByText("Self sign-up")).not.toBeInTheDocument();
  });
});
