import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { getSignInProviders } from "@/lib/api/auth";
import { getPendingIdentity } from "@/lib/api/signup";
import { joinWithIdentity } from "@/lib/api/signupJoin";
import type { PendingIdentity, SignInProviders } from "@/lib/api/types";
import { PracticeCompletionScreen } from "../PracticeCompletionScreen";

const replace = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace, push: vi.fn() }) }));

vi.mock("@/lib/api/auth", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/auth")>()),
  getSignInProviders: vi.fn(),
}));

vi.mock("@/lib/api/signup", () => ({ getPendingIdentity: vi.fn(), completeIdentitySignup: vi.fn() }));

vi.mock("@/lib/api/signupJoin", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/signupJoin")>()),
  joinWithIdentity: vi.fn(),
}));

const OPTIONS: SignInProviders = {
  providers: ["google"],
  signup: { enabled: true, terms_url: null, baa_url: null, privacy_url: null, test_data_only: true },
};

const IDENTITY: PendingIdentity = {
  email: "dana@lakeside.example.com",
  name: "Dana Fox",
  provider: "google",
  has_account: false,
  join: { practice_name: "Lakeside Primary Care", mode: "auto" },
};

describe("PracticeCompletionScreen with a claimed email domain", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getSignInProviders).mockResolvedValue(OPTIONS);
  });

  it("joins the practice and opens the app", async () => {
    vi.mocked(getPendingIdentity).mockResolvedValue(IDENTITY);
    vi.mocked(joinWithIdentity).mockResolvedValue({ access_token: "token-1", user: CODER });
    render(<PracticeCompletionScreen />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Join Lakeside Primary Care" }));
    expect(joinWithIdentity).toHaveBeenCalledWith({ name: "Dana Fox" });
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/today"));
  });

  it("asks to join and says the request was sent", async () => {
    vi.mocked(getPendingIdentity).mockResolvedValue({ ...IDENTITY, join: { practice_name: "Lakeside Primary Care", mode: "request" } });
    vi.mocked(joinWithIdentity).mockResolvedValue({ outcome: "requested" });
    render(<PracticeCompletionScreen />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Ask to join Lakeside Primary Care" }));
    expect(await screen.findByText("Request sent to Lakeside Primary Care")).toBeInTheDocument();
  });

  it("needs a name before joining", async () => {
    vi.mocked(getPendingIdentity).mockResolvedValue({ ...IDENTITY, name: "" });
    render(<PracticeCompletionScreen />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Join Lakeside Primary Care" }));
    expect(screen.getByText("Enter your name.")).toBeInTheDocument();
    expect(joinWithIdentity).not.toHaveBeenCalled();
  });

  it("creates a separate practice when the person chooses to", async () => {
    vi.mocked(getPendingIdentity).mockResolvedValue(IDENTITY);
    render(<PracticeCompletionScreen />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Create your own practice" }));
    expect(screen.getByLabelText("Practice name")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create practice" })).toBeInTheDocument();
  });
});
