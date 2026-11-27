import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CATALOG, planStatus, subscription } from "@/components/shared/plan-cards/__tests__/planFixtures";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { forgetRemote } from "@/hooks/remoteCache";
import { PLAN_CATALOG_KEY } from "@/hooks/usePlanCatalog";
import { PLAN_STATUS_KEY } from "@/hooks/usePlanStatus";
import { refreshSession } from "@/lib/api/client";
import { getPlanCatalog, getPlanStatus, startCheckout } from "@/lib/api/plan";
import { clearSession, setSession } from "@/lib/session/store";
import { leaveFor } from "../leaveFor";
import { PlanScreen } from "../PlanScreen";

const navigation = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(navigation.search),
  usePathname: () => "/settings/plan",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));
vi.mock("@/lib/api/plan", () => ({
  getPlanStatus: vi.fn(),
  getPlanCatalog: vi.fn(),
  startCheckout: vi.fn(),
  openBillingPortal: vi.fn(),
  cancelSubscription: vi.fn(),
}));
vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  refreshSession: vi.fn(),
  endSession: vi.fn(),
}));
vi.mock("../leaveFor", () => ({ leaveFor: vi.fn() }));

const CHECKOUT_URL = "https://checkout.stripe.com/c/pay/cs_test_1";
const ENDED = planStatus({ standing: "ended", renews_on: "2026-11-20", trial_days_left: 0 });
const ENDED_LINE = "Your practice's plan has ended";

function signInAdmin(billingOnly: boolean): void {
  setSession({ access_token: "token", user: { ...CODER, role: "admin", billing_only: billingOnly } });
}

function serve(status = ENDED, catalog = CATALOG): void {
  vi.mocked(getPlanStatus).mockResolvedValue(status);
  vi.mocked(getPlanCatalog).mockResolvedValue(catalog);
}

describe("PlanScreen after the plan has ended", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    forgetRemote(PLAN_STATUS_KEY);
    forgetRemote(PLAN_CATALOG_KEY);
    navigation.search = "";
  });

  afterEach(() => {
    vi.useRealTimers();
    clearSession();
  });

  it("says the plan has ended and keeps the choose-plan flow", async () => {
    signInAdmin(true);
    serve(ENDED, { ...CATALOG, providers: ["stripe"] });
    vi.mocked(startCheckout).mockResolvedValue({ url: CHECKOUT_URL });
    const user = userEvent.setup();
    render(<PlanScreen />);
    expect(screen.getByText(ENDED_LINE)).toBeInTheDocument();
    const summary = await screen.findByRole("region", { name: "Current plan" });
    expect(within(summary).getAllByText("Ended").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: "Choose plan" }));
    expect(startCheckout).toHaveBeenCalledWith({ plan: "essentials", interval: "monthly", provider: "stripe" });
    await waitFor(() => expect(leaveFor).toHaveBeenCalledWith(CHECKOUT_URL));
  });

  it("does not say the plan has ended to an admin whose plan is running", async () => {
    signInAdmin(false);
    serve(planStatus());
    render(<PlanScreen />);
    await screen.findByRole("region", { name: "Current plan" });
    expect(screen.queryByText(ENDED_LINE)).not.toBeInTheDocument();
  });

  it("renews the session after checkout so the app returns to normal once the subscription is active", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    navigation.search = "checkout=done";
    signInAdmin(true);
    serve();
    vi.mocked(refreshSession).mockImplementation(async () => {
      signInAdmin(false);
      return true;
    });
    render(<PlanScreen />);
    await screen.findByRole("region", { name: "Current plan" });
    expect(screen.getByText(ENDED_LINE)).toBeInTheDocument();
    const active = planStatus({ plan: "essentials", standing: "active", trial_days_left: null, subscription: subscription() });
    vi.mocked(getPlanStatus).mockResolvedValue(active);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(refreshSession).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(ENDED_LINE)).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Manage billing" })).toBeInTheDocument();
  });
});
