import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { forgetRemote } from "@/hooks/remoteCache";
import { getSignInProviders, switchPractice } from "@/lib/api/auth";
import { addLocation, addOrganizationPerson, getOrganization, grantOwnAccess, setCombinedBilling } from "@/lib/api/organizations";
import type { SignedIn } from "@/lib/api/types";
import { enterPractice } from "@/lib/session/practiceEntry";
import { clearSession, setSession } from "@/lib/session/store";
import { OrganizationPracticesScreen } from "../OrganizationPracticesScreen";
import { organizationKey } from "../useOrganizationData";
import { ORGANIZATION_ADMIN, ORGANIZATION_ID, OVERVIEW } from "./organizationFixtures";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));
vi.mock("@/lib/api/organizations", () => ({
  getOrganization: vi.fn(),
  setCombinedBilling: vi.fn(),
  grantOwnAccess: vi.fn(),
  addOrganizationPerson: vi.fn(),
  addLocation: vi.fn(),
}));
vi.mock("@/lib/api/auth", () => ({ switchPractice: vi.fn(), getSignInProviders: vi.fn() }));
vi.mock("@/lib/session/practiceEntry", () => ({ enterPractice: vi.fn() }));

const OPTIONS = {
  providers: [],
  signup: { enabled: true, terms_url: "https://example.com/terms", baa_url: "https://example.com/baa", privacy_url: null, test_data_only: false },
};

async function choose(combobox: string, option: string, events = userEvent.setup()): Promise<void> {
  await events.click(screen.getByRole("combobox", { name: combobox }));
  await events.click(screen.getByRole("option", { name: option }));
}

describe("OrganizationPracticesScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    forgetRemote(organizationKey(ORGANIZATION_ID));
    forgetRemote("sign-in-providers");
    setSession({ access_token: "token", user: ORGANIZATION_ADMIN });
    vi.mocked(getOrganization).mockResolvedValue(OVERVIEW);
    vi.mocked(getSignInProviders).mockResolvedValue(OPTIONS);
    vi.mocked(setCombinedBilling).mockResolvedValue(undefined);
    vi.mocked(grantOwnAccess).mockResolvedValue(undefined);
  });

  afterEach(() => clearSession());

  it("opens a practice the admin belongs to and offers access to the others", async () => {
    const switched: SignedIn = { access_token: "next", user: ORGANIZATION_ADMIN };
    vi.mocked(switchPractice).mockResolvedValue(switched);
    const events = userEvent.setup();
    render(<OrganizationPracticesScreen organizationId={ORGANIZATION_ID} />);
    await events.click(await screen.findByRole("button", { name: "Open Lakeside East" }));
    expect(switchPractice).toHaveBeenCalledWith("practice-3");
    await waitFor(() => expect(enterPractice).toHaveBeenCalledWith(switched));
    expect(screen.getByRole("button", { name: "Get access to Riverbend Clinic" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open Riverbend Clinic" })).not.toBeInTheDocument();
  });

  it("moves a practice out of combined billing and reloads the list", async () => {
    const events = userEvent.setup();
    render(<OrganizationPracticesScreen organizationId={ORGANIZATION_ID} />);
    const toggle = await screen.findByRole("switch", { name: "Combined billing for Lakeside East" });
    expect(toggle).toHaveAttribute("aria-checked", "true");
    await events.click(toggle);
    expect(setCombinedBilling).toHaveBeenCalledWith(ORGANIZATION_ID, "practice-3", false);
    await waitFor(() => expect(getOrganization).toHaveBeenCalledTimes(2));
  });

  it("gets access with a role and a reason, then opens the practice", async () => {
    vi.mocked(switchPractice).mockResolvedValue({ access_token: "next", user: ORGANIZATION_ADMIN });
    const events = userEvent.setup();
    render(<OrganizationPracticesScreen organizationId={ORGANIZATION_ID} />);
    await events.click(await screen.findByRole("button", { name: "Get access to Riverbend Clinic" }));
    const dialog = screen.getByRole("dialog", { name: "Access to Riverbend Clinic" });
    expect(within(dialog).getByRole("button", { name: "Get access" })).toBeDisabled();
    await choose("Role", "Coder", events);
    await events.type(within(dialog).getByRole("textbox", { name: "Reason" }), "Covering the front desk");
    await events.click(within(dialog).getByRole("button", { name: "Get access" }));
    expect(grantOwnAccess).toHaveBeenCalledWith(ORGANIZATION_ID, "practice-2", { role: "coder", reason: "Covering the front desk" });
    await events.click(await within(dialog).findByRole("button", { name: "Open Riverbend Clinic" }));
    expect(switchPractice).toHaveBeenCalledWith("practice-2");
  });

  it("adds a person to several practices with a role in each", async () => {
    vi.mocked(addOrganizationPerson).mockResolvedValue({ id: "user-9" });
    const events = userEvent.setup();
    render(<OrganizationPracticesScreen organizationId={ORGANIZATION_ID} />);
    await events.click(await screen.findByRole("button", { name: "Add person" }));
    const dialog = screen.getByRole("dialog", { name: "Add person" });
    await events.type(within(dialog).getByRole("textbox", { name: "Name" }), "Dana Fox");
    await events.type(within(dialog).getByRole("textbox", { name: "Email" }), "dana@acme.example.com");
    await events.click(within(dialog).getByRole("button", { name: "Add" }));
    expect(within(dialog).getByText("Choose a role in at least one practice")).toBeInTheDocument();
    expect(addOrganizationPerson).not.toHaveBeenCalled();
    await choose("Role in Lakeside East", "Biller", events);
    await choose("Role in Riverbend Clinic", "Viewer", events);
    await events.click(within(dialog).getByRole("button", { name: "Add" }));
    expect(addOrganizationPerson).toHaveBeenCalledWith(ORGANIZATION_ID, {
      name: "Dana Fox",
      email: "dana@acme.example.com",
      practices: [
        { practice_id: "practice-3", role: "biller" },
        { practice_id: "practice-2", role: "viewer" },
      ],
    });
    expect(await screen.findByText("Dana Fox added")).toBeInTheDocument();
  });

  it("adds a practice once the name is given and the terms are accepted", async () => {
    vi.mocked(addLocation).mockResolvedValue({ id: "practice-4" });
    const events = userEvent.setup();
    render(<OrganizationPracticesScreen organizationId={ORGANIZATION_ID} />);
    await events.click(await screen.findByRole("button", { name: "New practice" }));
    const dialog = screen.getByRole("dialog", { name: "New practice" });
    await events.click(within(dialog).getByRole("button", { name: "Create practice" }));
    expect(within(dialog).getByText("Enter the practice name")).toBeInTheDocument();
    await events.type(within(dialog).getByRole("textbox", { name: "Practice name" }), "Acme North");
    await events.click(await within(dialog).findByRole("checkbox", { name: "I agree to the Terms and BAA" }));
    await events.click(within(dialog).getByRole("button", { name: "Create practice" }));
    expect(addLocation).toHaveBeenCalledWith(ORGANIZATION_ID, { name: "Acme North", time_zone: expect.any(String), agreed: true });
    expect(await screen.findByText("Acme North added")).toBeInTheDocument();
  });
});
