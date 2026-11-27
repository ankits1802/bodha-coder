import { render, screen, within } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import HomePage from "@/app/(marketing)/page";
import { CATALOG, ESSENTIALS_TERMS, PROFESSIONAL_TERMS, TRIAL_TERMS } from "@/components/shared/plan-cards/__tests__/planFixtures";
import { forgetRemote } from "@/hooks/remoteCache";
import { PLAN_CATALOG_KEY } from "@/hooks/usePlanCatalog";
import { getPlanCatalog } from "@/lib/api/plan";
import { loadPlanCatalog } from "@/lib/api/planCatalogServer";
import type { PlanCatalog } from "@/lib/api/types";
import { PricingTeaser } from "../pricing/PricingTeaser";

vi.mock("@/lib/api/plan", () => ({ getPlanCatalog: vi.fn() }));
vi.mock("@/lib/api/planCatalogServer", () => ({ loadPlanCatalog: vi.fn() }));
vi.mock("@/lib/haptics", () => ({ haptic: vi.fn() }));

const RAISED: PlanCatalog = {
  ...CATALOG,
  plans: [TRIAL_TERMS, { ...ESSENTIALS_TERMS, monthly_cents: 19_900 }, { ...PROFESSIONAL_TERMS, monthly_cents: 32_900 }],
  trial_days: 21,
};

function plans(): string[] {
  return within(screen.getByRole("list", { name: "Plans" }))
    .getAllByRole("listitem")
    .map((item) => item.textContent ?? "");
}

beforeEach(() => {
  vi.resetAllMocks();
  forgetRemote(PLAN_CATALOG_KEY);
  vi.mocked(getPlanCatalog).mockResolvedValue(CATALOG);
});

describe("PricingTeaser", () => {
  it("shows the trial and the two plans priced per provider, a month, and links to the pricing page", () => {
    render(<PricingTeaser catalog={CATALOG} />);
    expect(screen.getByRole("heading", { level: 2, name: "Start free. Pay per provider." })).toBeInTheDocument();
    expect(plans()).toEqual([
      "TrialFreefor 14 daysNo card needed",
      "Essentials$149per provider / month",
      "Professional$249per provider / month",
    ]);
    expect(screen.queryByText("Enterprise")).toBeNull();
    expect(screen.getByRole("link", { name: "See all plans" })).toHaveAttribute("href", "/pricing");
    expect(getPlanCatalog).not.toHaveBeenCalled();
  });

  it("takes every price and the trial length from the catalog it is given", () => {
    render(<PricingTeaser catalog={RAISED} />);
    expect(plans()).toEqual([
      "TrialFreefor 21 daysNo card needed",
      "Essentials$199per provider / month",
      "Professional$329per provider / month",
    ]);
  });

  it("puts the prices in the server-rendered HTML", () => {
    const html = renderToString(<PricingTeaser catalog={CATALOG} />);
    for (const text of ["Free", "for 14 days", "$149", "$249", "per provider / month"]) expect(html).toContain(text);
  });

  it("loads the catalog in the browser when the server had none", async () => {
    render(<PricingTeaser catalog={null} />);
    expect(await screen.findByText("$149")).toBeInTheDocument();
    expect(screen.getByText("$249")).toBeInTheDocument();
    expect(getPlanCatalog).toHaveBeenCalledTimes(1);
  });

  it("offers a retry when the browser cannot load the catalog either", async () => {
    vi.mocked(getPlanCatalog).mockRejectedValue(new Error("Network error"));
    render(<PricingTeaser catalog={null} />);
    expect(await screen.findByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(screen.queryByText("$149")).toBeNull();
    expect(screen.getByRole("link", { name: "See all plans" })).toHaveAttribute("href", "/pricing");
  });
});

describe("home route", () => {
  it("renders the landing page with the catalog the server loaded", async () => {
    vi.mocked(loadPlanCatalog).mockResolvedValue(CATALOG);
    const html = renderToString(await HomePage());
    expect(html).toContain("Pay per provider.");
    expect(html).toContain("$149");
    expect(getPlanCatalog).not.toHaveBeenCalled();
  });

  it("falls back to the browser fetch when the backend cannot be reached", async () => {
    vi.mocked(loadPlanCatalog).mockResolvedValue(null);
    render(await HomePage());
    expect(await screen.findByText("$249")).toBeInTheDocument();
    expect(getPlanCatalog).toHaveBeenCalledTimes(1);
  });
});
