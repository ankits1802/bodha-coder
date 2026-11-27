import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { deletePractice, renewPractice, sendAdminLink, updatePractice } from "@/lib/api/hq";
import type { HqPractice } from "@/lib/api/types";
import { DeletePracticeDialog } from "../DeletePracticeDialog";
import { adminLinkLabel, canDeletePractice, confirmsDeletion, runPracticeAction } from "../practiceActions";

vi.mock("@/lib/api/hq", () => ({
  deletePractice: vi.fn(),
  renewPractice: vi.fn(),
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
  time_zone: "America/Chicago",
  source: "hq",
  signed_up_on: "2026-01-05",
  failed_24h: 0,
  last_failure: null,
  admin_name: "Priya Raman",
  admin_email: "priya@lakeside.example.com",
  admin_status: "invited",
};

describe("practice actions", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("deletes only an ended or blocked practice, confirmed by its exact name", () => {
    expect(canDeletePractice({ status: "blocked" })).toBe(true);
    expect(canDeletePractice({ status: "ended" })).toBe(true);
    expect(canDeletePractice({ status: "active" })).toBe(false);
    expect(canDeletePractice({ status: "trial" })).toBe(false);
    expect(confirmsDeletion(PRACTICE, "  Lakeside Primary Care ")).toBe(true);
    expect(confirmsDeletion(PRACTICE, "lakeside primary care")).toBe(false);
    expect(confirmsDeletion(PRACTICE, "Lakeside")).toBe(false);
  });

  it("offers an invited admin a new invite and an active admin a password reset", () => {
    expect(adminLinkLabel({ admin_status: "invited" })).toBe("Resend admin invite");
    expect(adminLinkLabel({ admin_status: "active" })).toBe("Send admin password reset");
  });

  it("reports what each action did", async () => {
    vi.mocked(renewPractice).mockResolvedValue({ renews_on: "2028-03-01" });
    vi.mocked(sendAdminLink).mockResolvedValue({ sent: "invite" });
    vi.mocked(deletePractice).mockResolvedValue(undefined);
    vi.mocked(updatePractice).mockResolvedValue(undefined);

    expect(await runPracticeAction({ kind: "renew", practice: PRACTICE })).toBe("Lakeside Primary Care renews 1 Mar 2028");
    expect(await runPracticeAction({ kind: "adminLink", practice: PRACTICE })).toBe("Invite sent to priya@lakeside.example.com");
    expect(await runPracticeAction({ kind: "delete", practice: PRACTICE }, "Lakeside Primary Care")).toBe("Lakeside Primary Care deleted");
    expect(deletePractice).toHaveBeenCalledWith("p1", "Lakeside Primary Care");
    expect(await runPracticeAction({ kind: "unblock", practice: PRACTICE })).toBeNull();
    expect(updatePractice).toHaveBeenCalledWith("p1", { status: "active" });
  });
});

describe("DeletePracticeDialog", () => {
  it("keeps the delete button off until the practice name is typed exactly", () => {
    const onConfirm = vi.fn();
    render(<DeletePracticeDialog practice={PRACTICE} pending={false} error={null} onConfirm={onConfirm} onClose={vi.fn()} />);
    const remove = screen.getByRole("button", { name: "Delete practice" });
    const typed = screen.getByLabelText("Type Lakeside Primary Care to confirm");

    expect(remove).toBeDisabled();
    fireEvent.change(typed, { target: { value: "Lakeside" } });
    expect(remove).toBeDisabled();
    fireEvent.change(typed, { target: { value: "Lakeside Primary Care" } });
    expect(remove).toBeEnabled();
    fireEvent.click(remove);
    expect(onConfirm).toHaveBeenCalledWith("Lakeside Primary Care");
  });
});
