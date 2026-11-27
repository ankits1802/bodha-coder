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
  closed_at: null,
  purge_after: null,
  purged_at: null,
  time_zone: "America/Chicago",
  source: "hq",
  signed_up_on: "2026-01-05",
  failed_24h: 0,
  last_failure: null,
  admin_name: "Priya Raman",
  admin_email: "priya@northside.example.com",
  admin_status: "active",
  billing_provider: null,
  billing_status: null,
  billing_interval: null,
};

const SELF: HqPractice = { ...BASE, id: "p2", name: "Harbor Pediatrics", status: "trial", plan: "trial", source: "self", signed_up_on: "2026-11-27" };

describe("PracticesTable", () => {
  it("marks a practice that signed itself up with a dot, the words and the day", () => {
    render(<PracticesTable practices={[BASE, SELF]} onEdit={vi.fn()} onAction={vi.fn()} onAppoint={vi.fn()} />);
    const harbor = screen.getByText("Harbor Pediatrics").closest("tr");
    const northside = screen.getByText("Northside Clinic").closest("tr");
    if (!harbor || !northside) throw new Error("rows not rendered");
    expect(within(harbor).getByText("Self sign-up")).toBeInTheDocument();
    expect(within(harbor).getByText("27 Nov 2026")).toBeInTheDocument();
    expect(within(northside).queryByText("Self sign-up")).not.toBeInTheDocument();
  });

  it("opens each practice's own page from its name", () => {
    render(<PracticesTable practices={[BASE, SELF]} onEdit={vi.fn()} onAction={vi.fn()} onAppoint={vi.fn()} />);
    expect(screen.getByRole("link", { name: "Northside Clinic" })).toHaveAttribute("href", "/hq/practices/p1");
    expect(screen.getByRole("link", { name: "Harbor Pediatrics" })).toHaveAttribute("href", "/hq/practices/p2");
  });

  it("shows how a paying practice pays and whether the payment is in good standing", () => {
    const paying: HqPractice = { ...BASE, billing_provider: "paypal", billing_status: "past_due", billing_interval: "annual" };
    render(<PracticesTable practices={[paying, SELF]} onEdit={vi.fn()} onAction={vi.fn()} onAppoint={vi.fn()} />);
    const northside = screen.getByText("Northside Clinic").closest("tr");
    const harbor = screen.getByText("Harbor Pediatrics").closest("tr");
    if (!harbor || !northside) throw new Error("rows not rendered");
    expect(within(northside).getByText("Past due · PayPal")).toBeInTheDocument();
    expect(within(harbor).queryByText(/Stripe|PayPal/)).not.toBeInTheDocument();
  });

  it("shows a closed practice with the day its records are kept until and offers nothing to change", () => {
    const closed: HqPractice = { ...BASE, status: "closed", closed_at: "2026-11-28T15:00:00Z", purge_after: "2099-11-28" };
    render(<PracticesTable practices={[closed]} onEdit={vi.fn()} onAction={vi.fn()} onAppoint={vi.fn()} />);
    const row = screen.getByText("Northside Clinic").closest("tr");
    if (!row) throw new Error("row not rendered");
    expect(within(row).getByText("Closed")).toBeInTheDocument();
    expect(within(row).getByText("Kept until 28 Nov 2099")).toBeInTheDocument();
    expect(within(row).queryByRole("button", { name: "More for Northside Clinic" })).not.toBeInTheDocument();
  });
});
