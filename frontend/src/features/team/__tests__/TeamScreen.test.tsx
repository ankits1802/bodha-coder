import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { forgetRemote } from "@/hooks/remoteCache";
import { ApiError } from "@/lib/api/errors";
import { getTeam, removeMember, updateMember } from "@/lib/api/team";
import type { TeamList, TeamMember } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { TeamScreen } from "../TeamScreen";

vi.mock("next/navigation", () => ({
  usePathname: () => "/team",
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/lib/api/team", () => ({
  getTeam: vi.fn(),
  inviteMember: vi.fn(),
  updateMember: vi.fn(),
  removeMember: vi.fn(),
  resetMemberMfa: vi.fn(),
  resendInvite: vi.fn(),
  sendPasswordReset: vi.fn(),
}));

const ADMIN: TeamMember = {
  id: "user-admin",
  name: "Practice Admin",
  email: "admin@lakeside.example.com",
  role: "admin",
  status: "active",
  mfa_enabled: true,
  last_active_at: new Date().toISOString(),
};
const SAM: TeamMember = { ...ADMIN, id: "user-sam", name: "Sam Patel", email: "sam@lakeside.example.com", role: "coder", mfa_enabled: false };
const ANA: TeamMember = { ...SAM, id: "user-ana", name: "Ana Ruiz", email: "ana@lakeside.example.com", role: "biller", status: "blocked" };
const TEAM: TeamList = { seats: 5, members: [ADMIN, ANA, SAM] };

async function choose(name: string, action: string): Promise<void> {
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: `More for ${name}` }));
  await user.click(screen.getByRole("menuitem", { name: action }));
}

describe("TeamScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    forgetRemote("team");
    setSession({ access_token: "token", user: { ...CODER, id: ADMIN.id, name: ADMIN.name, role: "admin" } });
    vi.mocked(getTeam).mockResolvedValue(TEAM);
    vi.mocked(removeMember).mockResolvedValue(undefined);
    vi.mocked(updateMember).mockResolvedValue(undefined);
  });

  afterEach(() => clearSession());

  it("counts seats from the practice's live memberships, leaving blocked ones out", async () => {
    render(<TeamScreen />);
    expect(await screen.findByText("2 of 5 seats")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "More for Practice Admin" })).toBeDisabled();
  });

  it("removes a member from this practice after a confirmation", async () => {
    render(<TeamScreen />);
    await choose("Sam Patel", "Remove");
    const dialog = screen.getByRole("dialog", { name: "Remove Sam Patel?" });
    await userEvent.setup().click(within(dialog).getByRole("button", { name: "Remove" }));
    expect(removeMember).toHaveBeenCalledWith("user-sam");
    await waitFor(() => expect(getTeam).toHaveBeenCalledTimes(2));
  });

  it("changes a role without telling the person to sign in again", async () => {
    render(<TeamScreen />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("combobox", { name: "Role for Sam Patel" }));
    await user.click(screen.getByRole("option", { name: "Biller" }));
    expect(updateMember).toHaveBeenCalledWith("user-sam", { role: "biller" });
    expect(await screen.findByText("Role changed for Sam Patel")).toBeInTheDocument();
  });

  it("shows why the last active admin cannot be blocked", async () => {
    vi.mocked(updateMember).mockRejectedValue(new ApiError(409, "conflict", "a practice needs at least one active admin"));
    render(<TeamScreen />);
    await choose("Sam Patel", "Block");
    const dialog = screen.getByRole("dialog", { name: "Block Sam Patel?" });
    await userEvent.setup().click(within(dialog).getByRole("button", { name: "Block" }));
    expect(await within(dialog).findByText(/at least one active admin/i)).toBeInTheDocument();
  });
});
