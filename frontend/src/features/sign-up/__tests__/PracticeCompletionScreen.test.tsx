import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getSignInProviders } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/errors";
import { completeIdentitySignup, getPendingIdentity } from "@/lib/api/signup";
import type { SignInProviders } from "@/lib/api/types";
import { openPage } from "../openPage";
import { PracticeCompletionScreen } from "../PracticeCompletionScreen";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

vi.mock("@/lib/api/auth", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/auth")>()),
  getSignInProviders: vi.fn(),
}));

vi.mock("@/lib/api/signup", () => ({ getPendingIdentity: vi.fn(), completeIdentitySignup: vi.fn() }));

vi.mock("../openPage", () => ({ openPage: vi.fn() }));

const OPTIONS: SignInProviders = {
  providers: ["microsoft"],
  signup: { enabled: true, terms_url: null, baa_url: null, privacy_url: null, test_data_only: true },
};

describe("PracticeCompletionScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getSignInProviders).mockResolvedValue(OPTIONS);
    vi.mocked(getPendingIdentity).mockResolvedValue({
      email: "omar@harbor.example.com",
      name: "Omar Haddad",
      provider: "microsoft",
    });
  });

  it("creates the practice for the signed-in account and continues to two-step setup", async () => {
    vi.mocked(completeIdentitySignup).mockResolvedValue({ mfa: "setup", mfa_token: "mfa-token-9" });
    const user = userEvent.setup();
    render(<PracticeCompletionScreen />);

    expect(await screen.findByText("omar@harbor.example.com")).toBeInTheDocument();
    expect(screen.getByLabelText("Your name")).toHaveValue("Omar Haddad");
    await user.type(screen.getByLabelText("Practice name"), "Harbor Pediatrics");
    await user.selectOptions(screen.getByLabelText("Time zone"), "America/New_York");
    await user.click(screen.getByRole("checkbox", { name: "I will use test data only" }));
    await user.click(screen.getByRole("button", { name: "Create practice" }));

    await waitFor(() =>
      expect(completeIdentitySignup).toHaveBeenCalledWith({
        name: "Omar Haddad",
        practice_name: "Harbor Pediatrics",
        time_zone: "America/New_York",
        agreed: true,
      }),
    );
    expect(openPage).toHaveBeenCalledWith("/sign-in#mfa=mfa-token-9&setup=1");
  });

  it("needs the agreement before creating the practice", async () => {
    const user = userEvent.setup();
    render(<PracticeCompletionScreen />);
    await user.type(await screen.findByLabelText("Practice name"), "Harbor Pediatrics");
    await user.click(screen.getByRole("button", { name: "Create practice" }));

    expect(screen.getByText("Tick the box to continue.")).toBeInTheDocument();
    expect(completeIdentitySignup).not.toHaveBeenCalled();
  });

  it("offers a new start when the sign-up has expired", async () => {
    vi.mocked(getPendingIdentity).mockRejectedValue(new ApiError(401, "unauthorized", "start sign-up again"));
    render(<PracticeCompletionScreen />);

    expect(await screen.findByText("This sign-up has expired.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Start again" })).toHaveAttribute("href", "/sign-up");
    expect(screen.queryByRole("button", { name: "Create practice" })).not.toBeInTheDocument();
  });
});
