import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getHqExpenditure, getHqPractices } from "@/lib/api/hq";
import { attachPractice, detachPractice, getHqOrganizationPage, setCombinedBilling } from "@/lib/api/hqOrganizations";
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

describe("HqOrganizationScreen", () => {
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

  it("opens on its practices with their own pages and how each is billed", async () => {
    render(<HqOrganizationScreen organizationId="o1" />);
    expect(await screen.findByRole("heading", { name: "Acme Health" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Lakeside Primary Care" })).toHaveAttribute("href", "/hq/practices/p1");
    expect(screen.getByRole("switch", { name: "Bill Lakeside Primary Care with the organization" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("switch", { name: "Bill Harbor Pediatrics with the organization" })).toHaveAttribute("aria-checked", "false");
    expect(within(rowOf("Harbor Pediatrics")).getAllByText("Trial")).toHaveLength(2);
  });

  it("moves a practice into combined billing and reads the page again", async () => {
    vi.mocked(setCombinedBilling).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<HqOrganizationScreen organizationId="o1" />);
    await user.click(await screen.findByRole("switch", { name: "Bill Harbor Pediatrics with the organization" }));
    await waitFor(() => expect(setCombinedBilling).toHaveBeenCalledWith("o1", "p2", true));
    await waitFor(() => expect(getHqOrganizationPage).toHaveBeenCalledTimes(2));
  });

  it("adds a practice that belongs to no organization", async () => {
    vi.mocked(attachPractice).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<HqOrganizationScreen organizationId="o1" />);
    await user.click(await screen.findByRole("button", { name: "Add practice" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a practice" });
    expect(await within(dialog).findByText("Northside Clinic")).toBeInTheDocument();
    expect(within(dialog).queryByText("Bayview")).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Add practice" }));
    await waitFor(() => expect(attachPractice).toHaveBeenCalledWith("o1", "p3"));
    expect(await screen.findByText("Northside Clinic added to the organization")).toBeInTheDocument();
  });

  it("removes a practice from the organization after confirming", async () => {
    vi.mocked(detachPractice).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<HqOrganizationScreen organizationId="o1" />);
    await user.click(await screen.findByRole("button", { name: "More for Lakeside Primary Care" }));
    await user.click(screen.getByRole("menuitem", { name: "Remove from organization" }));
    const dialog = await screen.findByRole("dialog", { name: "Remove Lakeside Primary Care from the organization?" });
    await user.click(within(dialog).getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(detachPractice).toHaveBeenCalledWith("o1", "p1"));
    expect(await screen.findByText("Lakeside Primary Care removed from the organization")).toBeInTheDocument();
  });
});
