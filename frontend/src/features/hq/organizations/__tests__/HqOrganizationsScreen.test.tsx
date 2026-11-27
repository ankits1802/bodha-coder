import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { addOrganization, getHqOrganizations } from "@/lib/api/hqOrganizations";
import type { HqOrganization } from "@/lib/api/types";
import { ACME } from "../../organization/__tests__/organizationFixtures";
import { HqOrganizationsScreen } from "../HqOrganizationsScreen";

vi.mock("@/lib/api/hqOrganizations", () => ({ getHqOrganizations: vi.fn(), addOrganization: vi.fn(), updateOrganization: vi.fn() }));

const CLOSED: HqOrganization = {
  ...ACME,
  id: "o2",
  name: "Bay Group",
  status: "closed",
  closed_at: "2026-11-20T10:00:00Z",
  purge_after: "2033-11-20",
  billing_provider: null,
  billing_status: null,
  billing_interval: null,
};

function rowOf(text: string): HTMLElement {
  const row = screen.getByText(text).closest("tr");
  if (!row) throw new Error(`no row for ${text}`);
  return row;
}

describe("HqOrganizationsScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getHqOrganizations).mockResolvedValue([ACME, CLOSED]);
  });

  it("lists each organization with its practices, plan, billing and status", async () => {
    render(<HqOrganizationsScreen />);
    expect(await screen.findByRole("link", { name: "Acme Health" })).toHaveAttribute("href", "/hq/organizations/o1");
    const acme = rowOf("Acme Health");
    expect(within(acme).getByText("2 practices · 1 billed together")).toBeInTheDocument();
    expect(within(acme).getByText("3 providers billed")).toBeInTheDocument();
    expect(within(acme).getByText("Paying · Stripe")).toBeInTheDocument();
    expect(within(acme).getByText("Active")).toBeInTheDocument();
    const bay = rowOf("Bay Group");
    expect(within(bay).getByText("Closed")).toBeInTheDocument();
    expect(within(bay).getByText("Kept until 20 Nov 2033")).toBeInTheDocument();
    expect(screen.getByText("2 organizations · 4 practices")).toBeInTheDocument();
  });

  it("adds an organization and lists it again", async () => {
    vi.mocked(addOrganization).mockResolvedValue({ id: "o3" });
    const user = userEvent.setup();
    render(<HqOrganizationsScreen />);
    await screen.findByText("Acme Health");
    await user.click(screen.getByRole("button", { name: "Add organization" }));
    const dialog = await screen.findByRole("dialog", { name: "Add organization" });
    await user.click(within(dialog).getByRole("button", { name: "Add organization" }));
    expect(within(dialog).getByText("Use at least 2 characters")).toBeInTheDocument();
    expect(addOrganization).not.toHaveBeenCalled();
    await user.type(within(dialog).getByLabelText("Organization name"), "Northwind Care");
    await user.click(within(dialog).getByRole("button", { name: "Add organization" }));
    await waitFor(() => expect(addOrganization).toHaveBeenCalledWith({ name: "Northwind Care", plan: "trial" }));
    expect(await screen.findByText("Northwind Care saved")).toBeInTheDocument();
    await waitFor(() => expect(getHqOrganizations).toHaveBeenCalledTimes(2));
  });

  it("says when there are no organizations", async () => {
    vi.mocked(getHqOrganizations).mockResolvedValue([]);
    render(<HqOrganizationsScreen />);
    expect(await screen.findByText("No organizations yet")).toBeInTheDocument();
  });
});
