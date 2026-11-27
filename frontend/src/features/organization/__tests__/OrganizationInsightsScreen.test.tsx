import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { forgetRemote } from "@/hooks/remoteCache";
import { getOrganizationInsights } from "@/lib/api/organizations";
import { OrganizationInsightsScreen } from "../OrganizationInsightsScreen";
import { organizationInsightsKey } from "../useOrganizationData";
import { INSIGHTS, ORGANIZATION_ID } from "./organizationFixtures";

const navigation = vi.hoisted(() => ({ search: "", replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(navigation.search),
  usePathname: () => "/organizations/org-1/insights",
  useRouter: () => ({ replace: navigation.replace, push: vi.fn() }),
}));
vi.mock("@/lib/api/organizations", () => ({ getOrganizationInsights: vi.fn() }));

describe("OrganizationInsightsScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    navigation.search = "";
    for (const days of [7, 14, 30, 90] as const) forgetRemote(organizationInsightsKey(ORGANIZATION_ID, days));
    vi.mocked(getOrganizationInsights).mockResolvedValue(INSIGHTS);
  });

  it("totals every practice and lists each one for the last 30 days", async () => {
    render(<OrganizationInsightsScreen organizationId={ORGANIZATION_ID} />);
    const totals = await screen.findByRole("region", { name: "All practices" });
    expect(getOrganizationInsights).toHaveBeenCalledWith(ORGANIZATION_ID, 30);
    expect(within(totals).getByText("52")).toBeInTheDocument();
    expect(within(totals).getByText("25")).toBeInTheDocument();
    expect(within(totals).getByText("60%")).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Each practice" });
    expect(within(table).getByRole("row", { name: /Lakeside Primary Care/ })).toHaveTextContent("50%");
    expect(within(table).getByRole("row", { name: /Riverbend Clinic/ })).toHaveTextContent("100%");
  });

  it("reads another period from the address and changes it", async () => {
    navigation.search = "days=7";
    const events = userEvent.setup();
    render(<OrganizationInsightsScreen organizationId={ORGANIZATION_ID} />);
    await screen.findByRole("region", { name: "All practices" });
    expect(getOrganizationInsights).toHaveBeenCalledWith(ORGANIZATION_ID, 7);
    await events.click(screen.getByRole("radio", { name: "90 days" }));
    expect(navigation.replace).toHaveBeenCalledWith("/organizations/org-1/insights?days=90", { scroll: false });
  });
});
