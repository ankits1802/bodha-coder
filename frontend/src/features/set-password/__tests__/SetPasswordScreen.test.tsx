import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { setPassword } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/errors";
import type { MfaChallenge, SignedIn } from "@/lib/api/types";
import { enterPractice } from "@/lib/session/practiceEntry";
import { SetPasswordScreen } from "../SetPasswordScreen";

vi.mock("@/lib/api/auth", () => ({ setPassword: vi.fn(), FORGOT_PASSWORD_PATH: "/forgot-password" }));
vi.mock("@/lib/session/practiceEntry", () => ({ enterPractice: vi.fn() }));

const PASSWORD = "harbor-view-2026";

async function choosePassword(): Promise<void> {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("New password"), PASSWORD);
  await user.type(screen.getByLabelText("Confirm password"), PASSWORD);
  await user.click(screen.getByRole("button", { name: "Set password" }));
}

function openLink(token: string): void {
  window.history.replaceState(null, "", `/set-password-${token}#${token}`);
  render(<SetPasswordScreen />);
}

describe("SetPasswordScreen", () => {
  beforeEach(() => vi.resetAllMocks());

  it("goes straight into the app once the password is set", async () => {
    const signedIn: SignedIn = { access_token: "fresh", user: CODER };
    vi.mocked(setPassword).mockResolvedValue(signedIn);
    openLink("invite-1");
    await choosePassword();
    expect(setPassword).toHaveBeenCalledWith("invite-1", PASSWORD);
    await waitFor(() => expect(enterPractice).toHaveBeenCalledWith(signedIn));
    expect(screen.queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("hands a role that needs two-step to its setup", async () => {
    const challenge: MfaChallenge = { mfa: "setup", mfa_token: "mfa-1" };
    vi.mocked(setPassword).mockResolvedValue(challenge);
    openLink("invite-2");
    await choosePassword();
    await waitFor(() => expect(enterPractice).toHaveBeenCalledWith(challenge));
  });

  it("stays on the form and offers a new link when the link has expired", async () => {
    vi.mocked(setPassword).mockRejectedValue(new ApiError(401, "unauthorized", "this link has expired"));
    openLink("invite-3");
    await choosePassword();
    expect(await screen.findByText(/this link has expired/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get a new link" })).toBeInTheDocument();
    expect(enterPractice).not.toHaveBeenCalled();
  });
});
