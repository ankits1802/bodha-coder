import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { forgetRemote } from "@/hooks/remoteCache";
import { getHqTeam, inviteHqMember, resendHqInvite, updateHqMember } from "@/lib/api/hq";
import { ApiError } from "@/lib/api/errors";
import type { HqTeamMember } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";
import { HQ_TEAM_KEY, HqTeamScreen } from "../HqTeamScreen";
import { hqMemberActions } from "../hqTeamModel";

vi.mock("@/lib/api/hq", () => ({
  getHqTeam: vi.fn(),
  inviteHqMember: vi.fn(),
  resendHqInvite: vi.fn(),
  updateHqMember: vi.fn(),
}));

const ANA: HqTeamMember = {
  id: "u-ana",
  name: "Ana Ortiz",
  email: "ana@bodha.example.com",
  status: "active",
  mfa_enabled: true,
  last_active_at: new Date().toISOString(),
};
const RAVI: HqTeamMember = { ...ANA, id: "u-ravi", name: "Ravi Menon", email: "ravi@bodha.example.com" };
const ASHA: HqTeamMember = {
  ...ANA,
  id: "u-asha",
  name: "Asha Rao",
  email: "asha@bodha.example.com",
  status: "invited",
  mfa_enabled: false,
  last_active_at: null,
};
const KIRAN: HqTeamMember = { ...RAVI, id: "u-kiran", name: "Kiran Shah", email: "kiran@bodha.example.com", status: "blocked" };

function signedInAs(member: HqTeamMember): void {
  setSession({
    access_token: "token",
    user: { id: member.id, name: member.name, email: member.email, role: "hq", billing_only: false, practice: null, practices: [] },
  });
}

function rowOf(name: string): HTMLElement {
  const row = screen.getByText(name).closest("tr");
  if (!row) throw new Error(`no row for ${name}`);
  return row;
}

async function choose(user: ReturnType<typeof userEvent.setup>, name: string, action: string): Promise<void> {
  await user.click(await screen.findByRole("button", { name: `More for ${name}` }));
  await user.click(await screen.findByRole("menuitem", { name: action }));
}

describe("hqMemberActions", () => {
  it("offers nothing on your own row and only what each status allows", () => {
    expect(hqMemberActions({ status: "active" }, true)).toEqual([]);
    expect(hqMemberActions({ status: "active" }, false)).toEqual(["deactivate"]);
    expect(hqMemberActions({ status: "invited" }, false)).toEqual(["resend", "deactivate"]);
    expect(hqMemberActions({ status: "blocked" }, false)).toEqual(["reactivate"]);
  });
});

describe("HqTeamScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    forgetRemote(HQ_TEAM_KEY);
    signedInAs(ANA);
    vi.mocked(getHqTeam).mockResolvedValue([ANA, ASHA, KIRAN, RAVI]);
  });

  afterEach(() => {
    clearSession();
  });

  it("lists every HQ account with its status, two-step and last activity", async () => {
    render(<HqTeamScreen />);
    await screen.findByText("Ana Ortiz");
    const ana = rowOf("Ana Ortiz");
    expect(within(ana).getByText("You")).toBeInTheDocument();
    expect(within(ana).getByText("Active")).toBeInTheDocument();
    expect(within(ana).getByText("On")).toBeInTheDocument();
    expect(within(ana).getByText("ana@bodha.example.com")).toBeInTheDocument();
    expect(within(ana).getByRole("button", { name: "More for Ana Ortiz" })).toBeDisabled();
    expect(within(rowOf("Asha Rao")).getByText("Invited")).toBeInTheDocument();
    expect(within(rowOf("Kiran Shah")).getByText("Deactivated")).toBeInTheDocument();
  });

  it("invites a person by name and email and reloads the list", async () => {
    vi.mocked(inviteHqMember).mockResolvedValue({ id: "u-new" });
    const user = userEvent.setup();
    render(<HqTeamScreen />);
    await screen.findByText("Ana Ortiz");
    await user.click(screen.getByRole("button", { name: "Invite" }));
    const dialog = screen.getByRole("dialog", { name: "Invite to HQ" });
    await user.type(within(dialog).getByLabelText("Name"), "Mira Das");
    await user.type(within(dialog).getByLabelText("Email"), "mira@bodha.example.com");
    await user.click(within(dialog).getByRole("button", { name: "Send invite" }));
    expect(inviteHqMember).toHaveBeenCalledWith({ name: "Mira Das", email: "mira@bodha.example.com" });
    await waitFor(() => expect(getHqTeam).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("dialog", { name: "Invite to HQ" })).not.toBeInTheDocument();
  });

  it("resends a pending invite and says where it went", async () => {
    vi.mocked(resendHqInvite).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<HqTeamScreen />);
    await screen.findByText("Asha Rao");
    await choose(user, "Asha Rao", "Resend invite");
    expect(resendHqInvite).toHaveBeenCalledWith("u-asha");
    expect(await screen.findByText("Invite sent to asha@bodha.example.com")).toBeInTheDocument();
  });

  it("deactivates and reactivates after confirming", async () => {
    vi.mocked(updateHqMember).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<HqTeamScreen />);
    await screen.findByText("Ravi Menon");
    await choose(user, "Ravi Menon", "Deactivate");
    await user.click(within(screen.getByRole("dialog", { name: "Deactivate Ravi Menon?" })).getByRole("button", { name: "Deactivate" }));
    expect(updateHqMember).toHaveBeenCalledWith("u-ravi", { blocked: true });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await choose(user, "Kiran Shah", "Reactivate");
    await user.click(within(screen.getByRole("dialog", { name: "Reactivate Kiran Shah?" })).getByRole("button", { name: "Reactivate" }));
    expect(updateHqMember).toHaveBeenCalledWith("u-kiran", { blocked: false });
  });

  it("keeps the dialog open with the server's reason when a deactivation is refused", async () => {
    vi.mocked(updateHqMember).mockRejectedValue(new ApiError(409, "conflict", "keep at least one active HQ account"));
    const user = userEvent.setup();
    render(<HqTeamScreen />);
    await screen.findByText("Ravi Menon");
    await choose(user, "Ravi Menon", "Deactivate");
    const dialog = screen.getByRole("dialog", { name: "Deactivate Ravi Menon?" });
    await user.click(within(dialog).getByRole("button", { name: "Deactivate" }));
    expect(await within(dialog).findByText("Keep at least one active HQ account")).toBeInTheDocument();
    expect(getHqTeam).toHaveBeenCalledTimes(1);
  });
});
