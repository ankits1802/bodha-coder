import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getSignInProviders, login, recoverMfa, verifyMfa } from "@/lib/api/auth";
import type { User } from "@/lib/api/types";
import { clearSession, getSession } from "@/lib/session/store";
import { SignInScreen } from "../SignInScreen";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/api/auth", () => ({
  FORGOT_PASSWORD_PATH: "/forgot-password",
  SIGN_UP_PATH: "/sign-up",
  providerStartPath: (provider: string) => `/api/auth/${provider}/start`,
  isSignedIn: (result: object) => "access_token" in result,
  login: vi.fn(),
  startMfaSetup: vi.fn(),
  verifyMfa: vi.fn(),
  recoverMfa: vi.fn(),
  getSignInProviders: vi.fn(),
}));

const SIGN_UP_OFF = { enabled: false, terms_url: null, baa_url: null, privacy_url: null, test_data_only: true };
const NO_EXTRAS = { providers: [], signup: SIGN_UP_OFF };

const ADMIN: User = {
  id: "user-1",
  name: "Practice Admin",
  email: "admin@lakeside.example.com",
  role: "admin",
  practice: {
    id: "practice-1",
    name: "Lakeside Primary Care",
    checks: { em: true, icd: true, cdi: true, audit: true, mips: false, hcc: false },
    idle_minutes: 15,
    time_zone: "America/Chicago",
  },
};

async function reachVerifyStep(): Promise<void> {
  render(<SignInScreen />);
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: ADMIN.email } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-horse-staple" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  fireEvent.click(await screen.findByRole("button", { name: "Use a recovery code" }));
}

describe("SignInScreen recovery codes", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getSignInProviders).mockResolvedValue(NO_EXTRAS);
    vi.mocked(login).mockResolvedValue({ mfa: "verify", mfa_token: "mfa-token-1" });
  });

  afterEach(() => {
    clearSession();
  });

  it("signs in with a recovery code in place of the six digits", async () => {
    vi.mocked(recoverMfa).mockResolvedValue({ access_token: "access-1", user: ADMIN });
    await reachVerifyStep();
    fireEvent.change(screen.getByLabelText("Recovery code"), { target: { value: "abcd-efgh-jkmn-pqrs" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() => expect(recoverMfa).toHaveBeenCalledWith("mfa-token-1", "abcd-efgh-jkmn-pqrs"));
    await waitFor(() => expect(getSession().user?.email).toBe(ADMIN.email));
    expect(verifyMfa).not.toHaveBeenCalled();
  });

  it("asks for all sixteen characters before sending a recovery code", async () => {
    await reachVerifyStep();
    fireEvent.change(screen.getByLabelText("Recovery code"), { target: { value: "abcd-efgh" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));

    expect(screen.getByText("Enter all 16 characters.")).toBeInTheDocument();
    expect(recoverMfa).not.toHaveBeenCalled();
  });

  it("goes back to the six-digit code", async () => {
    await reachVerifyStep();
    fireEvent.click(screen.getByRole("button", { name: "Use the 6-digit code" }));

    expect(screen.getByRole("group", { name: "Six-digit code" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Recovery code")).not.toBeInTheDocument();
  });
});

describe("SignInScreen other ways in", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    window.history.replaceState(null, "", "/");
  });

  it("offers each enabled sign-in service and the free trial", async () => {
    vi.mocked(getSignInProviders).mockResolvedValue({
      providers: ["google", "microsoft"],
      signup: { ...SIGN_UP_OFF, enabled: true },
    });
    render(<SignInScreen />);

    expect(await screen.findByRole("link", { name: "Continue with Microsoft" })).toHaveAttribute(
      "href",
      "/api/auth/microsoft/start",
    );
    expect(screen.getByRole("link", { name: "Continue with Google" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Continue with Yahoo" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Start a free trial" })).toHaveAttribute("href", "/sign-up");
  });

  it("hides the free trial when self sign-up is off", async () => {
    vi.mocked(getSignInProviders).mockResolvedValue({ providers: ["yahoo"], signup: SIGN_UP_OFF });
    render(<SignInScreen />);

    expect(await screen.findByRole("link", { name: "Continue with Yahoo" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Start a free trial" })).not.toBeInTheDocument();
  });

  it("names the service whose account has no verified email", async () => {
    vi.mocked(getSignInProviders).mockResolvedValue(NO_EXTRAS);
    window.history.replaceState(null, "", "/sign-in#error=unverified_email&provider=microsoft");
    render(<SignInScreen />);

    expect(await screen.findByText("This Microsoft account has no verified email.")).toBeInTheDocument();
  });
});
