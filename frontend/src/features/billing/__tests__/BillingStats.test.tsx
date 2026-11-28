import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { forgetRemote } from "@/hooks/remoteCache";
import { getBilling, getExports } from "@/lib/api/billing";
import type { BillingList } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";
import { BillingScreen } from "../BillingScreen";
import { billingPath } from "../billingRows";
import { billingWith, claimRow } from "./claimFixtures";

const search = vi.hoisted(() => ({ value: "" }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(search.value),
  usePathname: () => "/billing",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));
vi.mock("@/lib/api/billing", () => ({ getBilling: vi.fn(), downloadClaimLines: vi.fn(), getExports: vi.fn(), downloadExport: vi.fn() }));

const LIST: BillingList = { ...billingWith([claimRow("note-1", null)], null), summary: { ready: 7, exported_today: 4, held_for_provider: 2 } };

describe("billing summary", () => {
  beforeEach(() => {
    setSession({ access_token: "token", user: { ...CODER, role: "biller" } });
    vi.mocked(getBilling).mockResolvedValue(LIST);
    vi.mocked(getExports).mockResolvedValue({ items: [], total: 0, offset: 0, page_size: 50 });
  });

  afterEach(() => {
    clearSession();
    vi.mocked(getBilling).mockReset();
    for (const show of ["ready", "today"]) forgetRemote(`billing:${show}:0`);
    search.value = "";
  });

  it("opens the visits behind ready to bill and exported today and leaves the rest as text", async () => {
    render(<BillingScreen />);
    const summary = await screen.findByRole("region", { name: "Billing summary" });
    expect(within(summary).getByRole("link", { name: "Ready to bill, 7" })).toHaveAttribute("href", "/billing");
    expect(within(summary).getByRole("link", { name: "Exported today, 4" })).toHaveAttribute("href", "/billing?show=today");
    expect(within(summary).getAllByRole("link")).toHaveLength(2);
    expect(within(summary).getByText("Held for provider")).toBeInTheDocument();
  });

  it("lists the visits exported today from the address", async () => {
    search.value = "show=today";
    render(<BillingScreen />);
    await screen.findByRole("region", { name: "Billing summary" });
    expect(getBilling).toHaveBeenCalledWith("today", 0);
    expect(screen.getByRole("radio", { name: "Exported today" })).toHaveAttribute("aria-checked", "true");
  });

  it("writes each view's address, the default one without a query", () => {
    expect(billingPath("ready")).toBe("/billing");
    expect(billingPath("exported")).toBe("/billing?show=exported");
    expect(billingPath("today")).toBe("/billing?show=today");
  });
});
