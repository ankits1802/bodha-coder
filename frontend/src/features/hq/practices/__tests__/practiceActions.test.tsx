import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { closePractice, purgePractice, sendAdminLink, updatePractice } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { adminLinkLabel, canClosePractice, canPurgePractice, confirmsName, runPracticeAction } from "../practiceActions";
import { TypedNameDialog } from "../TypedNameDialog";

vi.mock("@/lib/api/hq", () => ({
  closePractice: vi.fn(),
  purgePractice: vi.fn(),
  sendAdminLink: vi.fn(),
  updatePractice: vi.fn(),
}));

const PRACTICE: HqPractice = {
  id: "p1",
  name: "Lakeside Primary Care",
  status: "blocked",
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
  admin_email: "priya@lakeside.example.com",
  admin_status: "invited",
  billing_provider: null,
  billing_status: null,
  billing_interval: null,
  organization_id: null,
  organization_name: null,
  combined_billing: false,
};

describe("practice actions", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("closes only an ended or blocked practice, confirmed by its exact name", () => {
    expect(canClosePractice({ status: "blocked" })).toBe(true);
    expect(canClosePractice({ status: "ended" })).toBe(true);
    expect(canClosePractice({ status: "active" })).toBe(false);
    expect(canClosePractice({ status: "closed" })).toBe(false);
    expect(confirmsName(PRACTICE, "  Lakeside Primary Care ")).toBe(true);
    expect(confirmsName(PRACTICE, "lakeside primary care")).toBe(false);
    expect(confirmsName(PRACTICE, "Lakeside")).toBe(false);
  });

  it("purges only a closed practice on or after its purge date", () => {
    const closed = { status: "closed" as const, purge_after: "2033-11-28" };
    expect(canPurgePractice(closed, "2033-11-27")).toBe(false);
    expect(canPurgePractice(closed, "2033-11-28")).toBe(true);
    expect(canPurgePractice({ status: "purged", purge_after: "2033-11-28" }, "2034-01-01")).toBe(false);
    expect(canPurgePractice({ status: "ended", purge_after: null }, "2034-01-01")).toBe(false);
  });

  it("offers an invited admin a new invite and an active admin a password reset", () => {
    expect(adminLinkLabel({ admin_status: "invited" })).toBe("Resend admin invite");
    expect(adminLinkLabel({ admin_status: "active" })).toBe("Send admin password reset");
  });

  it("reports what each action did", async () => {
    vi.mocked(sendAdminLink).mockResolvedValue({ sent: "invite" });
    vi.mocked(closePractice).mockResolvedValue(undefined);
    vi.mocked(purgePractice).mockResolvedValue({ access_log_entries: 1204, access_log_sha256: "ab".repeat(32) });
    vi.mocked(updatePractice).mockResolvedValue(undefined);

    expect(await runPracticeAction({ kind: "adminLink", practice: PRACTICE })).toBe("Invite sent to priya@lakeside.example.com");
    expect(await runPracticeAction({ kind: "close", practice: PRACTICE }, "Lakeside Primary Care")).toBe("Lakeside Primary Care closed");
    expect(closePractice).toHaveBeenCalledWith("p1", "Lakeside Primary Care");
    expect(await runPracticeAction({ kind: "purge", practice: PRACTICE }, "Lakeside Primary Care")).toBe(
      "Lakeside Primary Care purged · access log export of 1,204 entries kept",
    );
    expect(purgePractice).toHaveBeenCalledWith("p1", "Lakeside Primary Care");
    expect(await runPracticeAction({ kind: "unblock", practice: PRACTICE })).toBeNull();
    expect(updatePractice).toHaveBeenCalledWith("p1", { status: "active" });
  });
});

describe("TypedNameDialog", () => {
  it("keeps the close button off until the practice name is typed exactly", () => {
    const onConfirm = vi.fn();
    render(<TypedNameDialog kind="close" practice={PRACTICE} pending={false} error={null} onConfirm={onConfirm} onClose={vi.fn()} />);
    const close = screen.getByRole("button", { name: "Close practice" });
    const typed = screen.getByLabelText("Type Lakeside Primary Care to confirm");

    expect(close).toBeDisabled();
    fireEvent.change(typed, { target: { value: "Lakeside" } });
    expect(close).toBeDisabled();
    fireEvent.change(typed, { target: { value: "Lakeside Primary Care" } });
    expect(close).toBeEnabled();
    fireEvent.click(close);
    expect(onConfirm).toHaveBeenCalledWith("Lakeside Primary Care");
  });
});
