import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CATALOG, planStatus, subscription } from "@/components/shared/plan-cards/__tests__/planFixtures";
import { forgetRemote } from "@/hooks/remoteCache";
import { PLAN_CATALOG_KEY } from "@/hooks/usePlanCatalog";
import { PLAN_STATUS_KEY } from "@/hooks/usePlanStatus";
import { cancelSubscription, getPlanCatalog, getPlanStatus, openBillingPortal, startCheckout } from "@/lib/api/plan";
import { leaveFor } from "@/components/shared/plan-chooser/leaveFor";
import { PlanScreen } from "../PlanScreen";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(""),
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
vi.mock("@/components/shared/plan-chooser/leaveFor", () => ({ leaveFor: vi.fn() }));

const CHECKOUT_URL = "https://checkout.stripe.com/c/pay/cs_test_1";

function serve(status = planStatus(), catalog = CATALOG): void {
  vi.mocked(getPlanStatus).mockResolvedValue(status);
  vi.mocked(getPlanCatalog).mockResolvedValue(catalog);
}

describe("PlanScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    forgetRemote(PLAN_STATUS_KEY);
    forgetRemote(PLAN_CATALOG_KEY);
  });

  it("shows the trial with its days left and the use of each limit", async () => {
    serve();
    render(<PlanScreen />);
    const summary = await screen.findByRole("region", { name: "Current plan" });
    expect(within(summary).getByText("3 days left")).toBeInTheDocument();
    expect(within(summary).getByText("1 of 2")).toBeInTheDocument();
    expect(within(summary).getByText("1 of 5")).toBeInTheDocument();
    expect(within(summary).getAllByText("Trial").length).toBeGreaterThan(0);
  });

  it("chooses a plan and a period, then the payment method, and leaves for checkout", async () => {
    serve();
    vi.mocked(startCheckout).mockResolvedValue({ url: CHECKOUT_URL });
    const user = userEvent.setup();
    render(<PlanScreen />);
    await user.click(await screen.findByRole("radio", { name: "Professional" }));
    await user.click(screen.getByRole("radio", { name: "Annual 2 months free" }));
    expect(screen.getByText("$2,490")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Choose plan" }));
    const dialog = screen.getByRole("dialog", { name: "Pay with" });
    await user.click(within(dialog).getByRole("radio", { name: "PayPal" }));
    await user.click(within(dialog).getByRole("button", { name: "Continue" }));
    expect(startCheckout).toHaveBeenCalledWith({ plan: "professional", interval: "annual", provider: "paypal" });
    await waitFor(() => expect(leaveFor).toHaveBeenCalledWith(CHECKOUT_URL));
  });

  it("goes straight to checkout when one payment service is set up", async () => {
    serve(planStatus(), { ...CATALOG, providers: ["stripe"] });
    vi.mocked(startCheckout).mockResolvedValue({ url: CHECKOUT_URL });
    const user = userEvent.setup();
    render(<PlanScreen />);
    await user.click(await screen.findByRole("button", { name: "Choose plan" }));
    expect(screen.queryByRole("dialog", { name: "Pay with" })).not.toBeInTheDocument();
    expect(startCheckout).toHaveBeenCalledWith({ plan: "essentials", interval: "monthly", provider: "stripe" });
  });

  it("cannot start a checkout when no payment service is set up", async () => {
    serve(planStatus(), { ...CATALOG, providers: [] });
    render(<PlanScreen />);
    expect(await screen.findByRole("button", { name: "Choose plan" })).toBeDisabled();
    expect(screen.getByText("Online payment is not set up")).toBeInTheDocument();
  });

  it("sends a card subscriber to the billing portal", async () => {
    serve(planStatus({ plan: "essentials", standing: "active", trial_days_left: null, subscription: subscription() }));
    vi.mocked(openBillingPortal).mockResolvedValue({ url: "https://billing.stripe.com/p/session/test_1" });
    const user = userEvent.setup();
    render(<PlanScreen />);
    await user.click(await screen.findByRole("button", { name: "Manage billing" }));
    await waitFor(() => expect(leaveFor).toHaveBeenCalledWith("https://billing.stripe.com/p/session/test_1"));
    expect(screen.queryByRole("button", { name: "Choose plan" })).not.toBeInTheDocument();
  });

  it("lets a PayPal subscriber cancel at the end of the period after confirming", async () => {
    const paypal = subscription({ provider: "paypal", managed_by: "cancel" });
    serve(planStatus({ plan: "essentials", standing: "active", trial_days_left: null, subscription: paypal }));
    vi.mocked(cancelSubscription).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<PlanScreen />);
    await user.click(await screen.findByRole("button", { name: "Cancel at period end" }));
    const dialog = screen.getByRole("dialog", { name: "Cancel at the end of this period?" });
    await user.click(within(dialog).getByRole("button", { name: "Cancel subscription" }));
    expect(cancelSubscription).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("Cancellation requested")).toBeInTheDocument();
  });
});
