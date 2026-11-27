import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { forgetRemote } from "@/hooks/remoteCache";
import { PLAN_STATUS_KEY } from "@/hooks/usePlanStatus";
import { getPlanStatus } from "@/lib/api/plan";
import { localIsoDate } from "@/lib/dates";
import { planStatus } from "../../plan-cards/__tests__/planFixtures";
import { DISMISS_STORAGE_KEY, bannerFor } from "../bannerModel";
import { PlanBanner } from "../PlanBanner";

vi.mock("next/navigation", () => ({ usePathname: () => "/today" }));
vi.mock("@/lib/api/plan", () => ({ getPlanStatus: vi.fn() }));

describe("bannerFor", () => {
  it("counts down the trial and warns in its last three days", () => {
    expect(bannerFor(planStatus({ trial_days_left: 5 }))).toEqual({
      tone: "ok",
      text: "Your trial ends in 5 days",
      action: "Choose a plan",
    });
    expect(bannerFor(planStatus({ trial_days_left: 3 }))?.tone).toBe("warn");
    expect(bannerFor(planStatus({ trial_days_left: 1 }))?.text).toBe("Your trial ends tomorrow");
    expect(bannerFor(planStatus({ trial_days_left: 0 }))?.text).toBe("Your trial ends today");
  });

  it("names the last day of access after a failed payment", () => {
    expect(bannerFor(planStatus({ standing: "past_due", renews_on: "2026-12-08", trial_days_left: null }))).toEqual({
      tone: "warn",
      text: "Payment failed. Access continues until 8 Dec 2026",
      action: "Update payment",
    });
  });

  it("stays away from a paying or managed practice", () => {
    expect(bannerFor(planStatus({ standing: "active", trial_days_left: null }))).toBeNull();
    expect(bannerFor(planStatus({ standing: "managed", trial_days_left: null }))).toBeNull();
  });

  it("leaves an ended plan to the plan screen", () => {
    expect(bannerFor(planStatus({ standing: "ended", trial_days_left: 0 }))).toBeNull();
  });
});

describe("PlanBanner", () => {
  beforeEach(() => {
    window.localStorage.clear();
    forgetRemote(PLAN_STATUS_KEY);
    vi.mocked(getPlanStatus).mockReset();
  });

  it("shows an admin the trial with a link to the plan and hides it until tomorrow", async () => {
    vi.mocked(getPlanStatus).mockResolvedValue(planStatus({ trial_days_left: 5 }));
    const user = userEvent.setup();
    const { unmount } = render(<PlanBanner role="admin" />);
    expect(await screen.findByRole("status")).toHaveTextContent("Your trial ends in 5 days");
    expect(screen.getByRole("link", { name: "Choose a plan" })).toHaveAttribute("href", "/plan");
    await user.click(screen.getByRole("button", { name: "Hide until tomorrow" }));
    expect(screen.queryByText("Your trial ends in 5 days")).not.toBeInTheDocument();
    expect(window.localStorage.getItem(DISMISS_STORAGE_KEY)).toBe(localIsoDate());
    unmount();
    render(<PlanBanner role="admin" />);
    expect(screen.queryByText("Your trial ends in 5 days")).not.toBeInTheDocument();
  });

  it("asks nothing for another role", () => {
    render(<PlanBanner role="coder" />);
    expect(getPlanStatus).not.toHaveBeenCalled();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
