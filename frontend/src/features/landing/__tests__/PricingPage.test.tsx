import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CATALOG } from "@/components/shared/plan-cards/__tests__/planFixtures";
import { forgetRemote } from "@/hooks/remoteCache";
import { PLAN_CATALOG_KEY } from "@/hooks/usePlanCatalog";
import { getPlanCatalog } from "@/lib/api/plan";
import { PricingPage } from "../pricing/PricingPage";

vi.mock("@/lib/api/plan", () => ({ getPlanCatalog: vi.fn() }));
vi.mock("@/lib/haptics", () => ({ haptic: vi.fn() }));

describe("PricingPage", () => {
  beforeEach(() => {
    forgetRemote(PLAN_CATALOG_KEY);
    vi.mocked(getPlanCatalog).mockResolvedValue(CATALOG);
  });

  it("shows every plan with its price per provider and switches to yearly prices", async () => {
    const user = userEvent.setup();
    render(<PricingPage />);
    expect(screen.getByRole("heading", { level: 1, name: "Pricing" })).toBeInTheDocument();
    for (const name of ["Trial", "Essentials", "Professional", "Enterprise"]) {
      expect(await screen.findByRole("heading", { level: 3, name })).toBeInTheDocument();
    }
    expect(screen.getByText("$149")).toBeInTheDocument();
    expect(screen.getByText("$249")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "Annual 2 months free" }));
    expect(screen.getByText("$1,490")).toBeInTheDocument();
    expect(screen.getByText("$2,490")).toBeInTheDocument();
  });

  it("starts a free trial from each listed plan and asks for a demo for enterprise", async () => {
    render(<PricingPage />);
    await screen.findByRole("heading", { level: 3, name: "Enterprise" });
    const plans = screen.getByRole("region", { name: "Plans" });
    const trials = plans.querySelectorAll('a[href="/sign-up"]');
    expect(trials).toHaveLength(3);
    expect(screen.getByRole("button", { name: "Request a demo" })).toBeInTheDocument();
  });

  it("links Pricing from the nav and the sections back to the landing page", () => {
    render(<PricingPage />);
    expect(screen.getAllByRole("link", { name: "Pricing" })[0]).toHaveAttribute("href", "/pricing");
    expect(screen.getAllByRole("link", { name: "How it works" })[0]).toHaveAttribute("href", "/#how");
  });
});
