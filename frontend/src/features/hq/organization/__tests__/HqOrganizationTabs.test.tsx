import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getHqExpenditure, getHqPractices } from "@/lib/api/hq";
import { addOrganizationAdmin, getHqOrganizationPage, removeOrganizationAdmin, renewOrganization } from "@/lib/api/hqOrganizations";
import { QUIET_SPEND } from "../../practice/__tests__/practiceFixtures";
import { HqOrganizationScreen } from "../HqOrganizationScreen";
import { ACME_PAGE, ELSEWHERE, UNATTACHED } from "./organizationFixtures";

const navigation = vi.hoisted(() => ({ search: "", replace: vi.fn() }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(navigation.search),
  usePathname: () => "/hq/organizations/o1",
  useRouter: () => ({ replace: navigation.replace, push: vi.fn() }),
}));
vi.mock("@/lib/api/hq", () => ({ getHqPractices: vi.fn(), getHqExpenditure: vi.fn() }));
vi.mock("@/lib/api/hqOrganizations", () => ({
  getHqOrganizationPage: vi.fn(),
  setCombinedBilling: vi.fn(),
  detachPractice: vi.fn(),
  attachPractice: vi.fn(),
  addOrganizationAdmin: vi.fn(),
  removeOrganizationAdmin: vi.fn(),
  renewOrganization: vi.fn(),
  updateOrganization: vi.fn(),
  addOrganization: vi.fn(),
  closeOrganization: vi.fn(),
  purgeOrganization: vi.fn(),
}));

function rowOf(text: string): HTMLElement {
  const row = screen.getByText(text).closest("tr");
  if (!row) throw new Error(`no row for ${text}`);
  return row;
}

describe("HqOrganizationScreen tabs", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-28T12:00:00Z"));
    navigation.search = "";
    vi.mocked(getHqOrganizationPage).mockResolvedValue(ACME_PAGE);
    vi.mocked(getHqPractices).mockResolvedValue([ELSEWHERE, UNATTACHED]);
    vi.mocked(getHqExpenditure).mockResolvedValue(QUIET_SPEND);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("adds and removes organization admins", async () => {
    navigation.search = "tab=admins";
    vi.mocked(addOrganizationAdmin).mockResolvedValue({ id: "u2" });
    vi.mocked(removeOrganizationAdmin).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<HqOrganizationScreen organizationId="o1" />);
    expect(await screen.findByText("dana@acme.example.com")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add admin" }));
    const dialog = await screen.findByRole("dialog", { name: "Add an admin to Acme Health" });
    await user.type(within(dialog).getByLabelText("Email"), "lee@acme.example.com");
    await user.type(within(dialog).getByLabelText("Reason"), "Runs the group");
    await user.click(within(dialog).getByRole("button", { name: "Add admin" }));
    await waitFor(() => expect(addOrganizationAdmin).toHaveBeenCalledWith("o1", { email: "lee@acme.example.com", reason: "Runs the group" }));
    await user.click(await screen.findByRole("button", { name: "Remove Dana Fox" }));
    const confirm = await screen.findByRole("dialog", { name: "Remove Dana Fox as an admin?" });
    await user.click(within(confirm).getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(removeOrganizationAdmin).toHaveBeenCalledWith("o1", "u1"));
  });

  it("shows the combined plan with each practice's usage", async () => {
    navigation.search = "tab=plan";
    render(<HqOrganizationScreen organizationId="o1" />);
    expect(await screen.findByText("Paying · Stripe")).toBeInTheDocument();
    expect(within(rowOf("Lakeside Primary Care")).getByText("3 of 50")).toBeInTheDocument();
    expect(within(rowOf("Lakeside Primary Care")).getByText("4")).toBeInTheDocument();
  });

  it("reads spend for the practices of the organization", async () => {
    navigation.search = "tab=spend";
    render(<HqOrganizationScreen organizationId="o1" />);
    await waitFor(() => expect(getHqExpenditure).toHaveBeenCalledWith({ from: "2026-11-01", to: "2026-11-28" }, { organization_id: "o1" }));
  });

  it("renews the organization by hand", async () => {
    vi.mocked(renewOrganization).mockResolvedValue({ renews_on: "2100-03-01" });
    const user = userEvent.setup();
    render(<HqOrganizationScreen organizationId="o1" />);
    await user.click(await screen.findByRole("button", { name: "Renew" }));
    const dialog = await screen.findByRole("dialog", { name: "Renew Acme Health" });
    await user.click(within(dialog).getByRole("button", { name: "Renew" }));
    await waitFor(() => expect(renewOrganization).toHaveBeenCalledWith("o1", "2100-03-01"));
    expect(await screen.findByText("Acme Health renews 1 Mar 2100")).toBeInTheDocument();
  });

  it("offers no changes for a closed organization", async () => {
    vi.mocked(getHqOrganizationPage).mockResolvedValue({
      ...ACME_PAGE,
      organization: { ...ACME_PAGE.organization, status: "closed", closed_at: "2026-11-27T10:00:00Z", purge_after: "2099-11-27" },
    });
    render(<HqOrganizationScreen organizationId="o1" />);
    expect(await screen.findByRole("heading", { name: "Acme Health" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Renew" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add practice" })).not.toBeInTheDocument();
    expect(screen.getByRole("switch", { name: "Bill Lakeside Primary Care with the organization" })).toBeDisabled();
  });
});
