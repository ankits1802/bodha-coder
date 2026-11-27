import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { forgetRemote } from "@/hooks/remoteCache";
import { getSignInProviders, startPractice } from "@/lib/api/auth";
import type { SignInProviders } from "@/lib/api/types";
import { enterPractice } from "@/lib/session/practiceEntry";
import { NewPracticeScreen } from "../NewPracticeScreen";

vi.mock("@/lib/api/auth", () => ({ getSignInProviders: vi.fn(), startPractice: vi.fn() }));
vi.mock("@/lib/session/practiceEntry", () => ({ enterPractice: vi.fn() }));

const OPTIONS: SignInProviders = {
  providers: [],
  signup: { enabled: true, terms_url: null, baa_url: null, privacy_url: null, test_data_only: true },
};

describe("NewPracticeScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    forgetRemote("sign-in-providers");
    vi.mocked(getSignInProviders).mockResolvedValue(OPTIONS);
  });

  it("starts a practice for the signed-in person and opens it", async () => {
    vi.mocked(startPractice).mockResolvedValue({ mfa: "setup", mfa_token: "mfa-1" });
    const user = userEvent.setup();
    render(<NewPracticeScreen />);
    expect(screen.queryByLabelText("Your name")).not.toBeInTheDocument();
    await user.type(await screen.findByLabelText("Practice name"), "Harbor Pediatrics");
    await user.click(screen.getByRole("checkbox", { name: "I will use test data only" }));
    await user.click(screen.getByRole("button", { name: "Create practice" }));
    await waitFor(() => expect(enterPractice).toHaveBeenCalledWith({ mfa: "setup", mfa_token: "mfa-1" }));
    expect(vi.mocked(startPractice).mock.calls[0]?.[0]).toMatchObject({ practice_name: "Harbor Pediatrics", agreed: true });
  });

  it("needs the agreement", async () => {
    const user = userEvent.setup();
    render(<NewPracticeScreen />);
    await user.type(await screen.findByLabelText("Practice name"), "Harbor Pediatrics");
    await user.click(screen.getByRole("button", { name: "Create practice" }));
    expect(screen.getByText("Tick the box to continue.")).toBeInTheDocument();
    expect(startPractice).not.toHaveBeenCalled();
  });

  it("says so when sign-up is closed", async () => {
    vi.mocked(getSignInProviders).mockResolvedValue({ ...OPTIONS, signup: { ...OPTIONS.signup, enabled: false } });
    render(<NewPracticeScreen />);
    expect(await screen.findByText("Self sign-up is not available.")).toBeInTheDocument();
  });
});
