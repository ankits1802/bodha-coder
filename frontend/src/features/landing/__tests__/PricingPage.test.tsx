import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderToString } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PricingRoute from "@/app/(marketing)/pricing/page";
import { CATALOG } from "@/components/shared/plan-cards/__tests__/planFixtures";
import { forgetRemote } from "@/hooks/remoteCache";
import { PLAN_CATALOG_KEY } from "@/hooks/usePlanCatalog";
import { getPlanCatalog } from "@/lib/api/plan";
import { loadPlanCatalog } from "@/lib/api/planCatalogServer";
import { PricingPage } from "../pricing/PricingPage";

vi.mock("@/lib/api/plan", () => ({ getPlanCatalog: vi.fn() }));
vi.mock("@/lib/api/planCatalogServer", () => ({ loadPlanCatalog: vi.fn() }));
vi.mock("@/lib/haptics", () => ({ haptic: vi.fn() }));

const PAGE = "https://www.bodhaai.co/pricing";

interface Offer {
  url: string;
  price: string;
  priceCurrency: string;
  priceSpecification: { unitText: string; referenceQuantity: { value: number; unitCode: string } };
}

interface Product {
  "@type": string;
  name: string;
  description: string;
  offers: Offer[];
}

function structuredData(): { "@context": string; "@graph": Product[] } | null {
  const script = document.querySelector('script[type="application/ld+json"]');
  return script ? JSON.parse(script.textContent ?? "") : null;
}

beforeEach(() => {
  vi.resetAllMocks();
  forgetRemote(PLAN_CATALOG_KEY);
  vi.mocked(getPlanCatalog).mockResolvedValue(CATALOG);
  vi.stubEnv("SITE_URL", "https://www.bodhaai.co");
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("PricingPage", () => {
  it("puts every plan name and monthly price in the server-rendered HTML", () => {
    const html = renderToString(<PricingPage catalog={CATALOG} />);
    for (const text of ["Trial", "Essentials", "Professional", "Enterprise", "$149", "$249", "per provider / month"]) {
      expect(html).toContain(text);
    }
    expect(getPlanCatalog).not.toHaveBeenCalled();
  });

  it("describes the two priced plans as products with a monthly and a yearly offer", () => {
    render(<PricingPage catalog={CATALOG} />);
    const data = structuredData();
    expect(data?.["@context"]).toBe("https://schema.org");
    const graph = data?.["@graph"] ?? [];
    expect(graph.map((product) => [product["@type"], product.name, product.description])).toEqual([
      ["Product", "Bodha Coder Essentials", "Up to 5 users. Up to 3 providers. Every feature included"],
      ["Product", "Bodha Coder Professional", "Unlimited users. Up to 50 providers. Every feature included"],
    ]);
    const offers = graph.flatMap((product) => product.offers);
    expect(offers.map((offer) => [offer.price, offer.priceCurrency, offer.priceSpecification.referenceQuantity.unitCode, offer.url])).toEqual([
      ["149.00", "USD", "MON", PAGE],
      ["1490.00", "USD", "ANN", PAGE],
      ["249.00", "USD", "MON", PAGE],
      ["2490.00", "USD", "ANN", PAGE],
    ]);
    expect(offers.map((offer) => offer.priceSpecification.unitText)).toEqual([
      "per provider / month",
      "per provider / year",
      "per provider / month",
      "per provider / year",
    ]);
  });

  it("switches the prices it was given to yearly", async () => {
    const user = userEvent.setup();
    render(<PricingPage catalog={CATALOG} />);
    expect(screen.getByRole("heading", { level: 1, name: "Pricing" })).toBeInTheDocument();
    expect(screen.getByText("$149")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "Annual 2 months free" }));
    expect(screen.getByText("$1,490")).toBeInTheDocument();
    expect(screen.getByText("$2,490")).toBeInTheDocument();
  });

  it("loads the plans in the browser when the server had none, without structured data", async () => {
    render(<PricingPage catalog={null} />);
    for (const name of ["Trial", "Essentials", "Professional", "Enterprise"]) {
      expect(await screen.findByRole("heading", { level: 3, name })).toBeInTheDocument();
    }
    expect(screen.getByText("$149")).toBeInTheDocument();
    expect(screen.getByText("$249")).toBeInTheDocument();
    expect(getPlanCatalog).toHaveBeenCalledTimes(1);
    expect(structuredData()).toBeNull();
  });

  it("starts a free trial from each listed plan and asks for a demo for enterprise", () => {
    render(<PricingPage catalog={CATALOG} />);
    const plans = screen.getByRole("region", { name: "Plans" });
    expect(plans.querySelectorAll('a[href="/sign-up"]')).toHaveLength(3);
    expect(screen.getByRole("button", { name: "Request a demo" })).toBeInTheDocument();
  });

  it("links Pricing from the nav and the sections back to the landing page", () => {
    render(<PricingPage catalog={CATALOG} />);
    expect(screen.getAllByRole("link", { name: "Pricing" })[0]).toHaveAttribute("href", "/pricing");
    expect(screen.getAllByRole("link", { name: "How it works" })[0]).toHaveAttribute("href", "/#how");
  });
});

describe("pricing route", () => {
  it("renders the catalog the server loaded", async () => {
    vi.mocked(loadPlanCatalog).mockResolvedValue(CATALOG);
    const html = renderToString(await PricingRoute());
    expect(html).toContain("$149");
    expect(html).toContain("application/ld+json");
    expect(getPlanCatalog).not.toHaveBeenCalled();
  });

  it("falls back to loading the plans in the browser when the backend cannot be reached", async () => {
    vi.mocked(loadPlanCatalog).mockResolvedValue(null);
    render(await PricingRoute());
    expect(await screen.findByText("$149")).toBeInTheDocument();
    expect(getPlanCatalog).toHaveBeenCalledTimes(1);
  });
});
