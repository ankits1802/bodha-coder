import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CATALOG, subscription } from "@/components/shared/plan-cards/__tests__/planFixtures";
import { leaveFor } from "@/components/shared/plan-chooser/leaveFor";
import { forgetRemote } from "@/hooks/remoteCache";
import { PLAN_CATALOG_KEY } from "@/hooks/usePlanCatalog";
import { getOrganizationPlan, openOrganizationPortal, startOrganizationCheckout } from "@/lib/api/organizations";
import { getPlanCatalog } from "@/lib/api/plan";
import { canOpenPath } from "@/lib/roles";
import { clearSession, setSession } from "@/lib/session/store";
import { OrganizationPlanScreen } from "../OrganizationPlanScreen";
import { organizationPlanKey } from "../useOrganizationData";
import { ORGANIZATION_ADMIN, ORGANIZATION_ID, organizationPlan } from "./organizationFixtures";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(""),
  usePathname: () => "/organizations/org-1/plan",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));
vi.mock("@/lib/api/organizations", () => ({
  getOrganizationPlan: vi.fn(),
  startOrganizationCheckout: vi.fn(),
  openOrganizationPortal: vi.fn(),
  cancelOrganizationSubscription: vi.fn(),
}));
vi.mock("@/lib/api/plan", () => ({ getPlanCatalog: vi.fn() }));
vi.mock("@/components/shared/plan-chooser/leaveFor", () => ({ leaveFor: vi.fn() }));

const CHECKOUT_URL = "https://checkout.stripe.com/c/pay/cs_test_org";
const BILLING_ONLY = { ...ORGANIZATION_ADMIN, billing_only: true };

describe("OrganizationPlanScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    forgetRemote(organizationPlanKey(ORGANIZATION_ID));
    forgetRemote(PLAN_CATALOG_KEY);
    vi.mocked(getPlanCatalog).mockResolvedValue(CATALOG);
  });

  afterEach(() => clearSession());

  it("lets a billing-only organization admin pay for every combined practice", async () => {
    setSession({ access_token: "token", user: BILLING_ONLY });
    expect(canOpenPath(BILLING_ONLY, "/organizations/org-1/plan")).toBe(true);
    vi.mocked(getOrganizationPlan).mockResolvedValue(organizationPlan({ standing: "ended", renews_on: "2026-11-20" }));
    vi.mocked(startOrganizationCheckout).mockResolvedValue({ url: CHECKOUT_URL });
    const events = userEvent.setup();
    render(<OrganizationPlanScreen organizationId={ORGANIZATION_ID} />);
    expect(await screen.findByText("The organization's plan has ended")).toBeInTheDocument();
    const usage = screen.getByRole("table", { name: "Practices in combined billing" });
    expect(within(usage).getByRole("row", { name: /Lakeside Primary Care/ })).toHaveTextContent("3 of 50");
    await events.click(await screen.findByRole("radio", { name: "Professional" }));
    await events.click(screen.getByRole("button", { name: "Choose plan" }));
    await events.click(within(screen.getByRole("dialog", { name: "Pay with" })).getByRole("button", { name: "Continue" }));
    expect(startOrganizationCheckout).toHaveBeenCalledWith(ORGANIZATION_ID, { plan: "professional", interval: "monthly", provider: "stripe" });
    await waitFor(() => expect(leaveFor).toHaveBeenCalledWith(CHECKOUT_URL));
  });

  it("opens the organization's billing portal while a card subscription is live", async () => {
    setSession({ access_token: "token", user: ORGANIZATION_ADMIN });
    vi.mocked(getOrganizationPlan).mockResolvedValue(
      organizationPlan({ plan: "professional", standing: "active", subscription: subscription({ quantity: 4 }) }),
    );
    vi.mocked(openOrganizationPortal).mockResolvedValue({ url: "https://billing.stripe.com/p/session/org" });
    const events = userEvent.setup();
    render(<OrganizationPlanScreen organizationId={ORGANIZATION_ID} />);
    await events.click(await screen.findByRole("button", { name: "Manage billing" }));
    expect(openOrganizationPortal).toHaveBeenCalledWith(ORGANIZATION_ID);
    await waitFor(() => expect(leaveFor).toHaveBeenCalledWith("https://billing.stripe.com/p/session/org"));
    expect(screen.queryByRole("button", { name: "Choose plan" })).not.toBeInTheDocument();
  });
});
