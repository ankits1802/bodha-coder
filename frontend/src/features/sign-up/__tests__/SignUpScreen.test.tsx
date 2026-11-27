import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getSignInProviders } from "@/lib/api/auth";
import { requestSignup } from "@/lib/api/signup";
import type { SignInProviders } from "@/lib/api/types";
import { SignUpScreen } from "../SignUpScreen";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/api/auth", () => ({
  getSignInProviders: vi.fn(),
  providerStartPath: (provider: string) => `/api/auth/${provider}/start`,
}));

vi.mock("@/lib/api/signup", () => ({ requestSignup: vi.fn() }));

const TEST_DATA: SignInProviders = {
  providers: [],
  signup: { enabled: true, terms_url: null, baa_url: null, privacy_url: null, test_data_only: true },
};

const LEGAL: SignInProviders = {
  providers: ["google", "microsoft"],
  signup: {
    enabled: true,
    terms_url: "https://bodha.example.com/terms",
    baa_url: "https://bodha.example.com/baa",
    privacy_url: "https://bodha.example.com/privacy",
    test_data_only: false,
  },
};

async function fillForm(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.type(screen.getByLabelText("Your name"), "Rosa Diaz");
  await user.type(screen.getByLabelText("Practice name"), "Lakeside Family Medicine");
  await user.type(screen.getByLabelText("Work email"), "rosa@lakeside.example.com");
  await user.selectOptions(screen.getByLabelText("Time zone"), "America/Denver");
}

describe("SignUpScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getSignInProviders).mockResolvedValue(TEST_DATA);
  });

  it("checks each field when it loses focus and every field before sending", async () => {
    render(<SignUpScreen />);
    const email = await screen.findByLabelText("Work email");
    fireEvent.change(email, { target: { value: "rosa@" } });
    fireEvent.blur(email);
    expect(screen.getByText("Enter a valid email.")).toBeInTheDocument();
    expect(screen.queryByText("Enter your name.")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Create practice" }));
    expect(screen.getByText("Enter your name.")).toBeInTheDocument();
    expect(screen.getByText("Enter at least 2 characters.")).toBeInTheDocument();
    expect(screen.getByText("Tick the box to continue.")).toBeInTheDocument();
    expect(requestSignup).not.toHaveBeenCalled();
  });

  it("asks for test data only when no business associate agreement is published", async () => {
    render(<SignUpScreen />);
    expect(await screen.findByRole("checkbox", { name: "I will use test data only" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "BAA" })).not.toBeInTheDocument();
  });

  it("links the published terms, agreement and privacy policy from the checkbox", async () => {
    vi.mocked(getSignInProviders).mockResolvedValue(LEGAL);
    render(<SignUpScreen />);
    const name = "I agree to the Terms, BAA, and Privacy Policy";
    expect(await screen.findByRole("checkbox", { name })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "BAA" })).toHaveAttribute("href", "https://bodha.example.com/baa");
    expect(screen.getByRole("link", { name: "Terms" })).toHaveAttribute("target", "_blank");
    expect(screen.getByRole("link", { name: "Continue with Google" })).toHaveAttribute("href", "/api/auth/google/start");
    expect(screen.getByRole("link", { name: "Continue with Microsoft" })).toBeInTheDocument();
  });

  it("sends the request and shows where the link went", async () => {
    vi.mocked(requestSignup).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<SignUpScreen />);
    await screen.findByLabelText("Work email");
    await fillForm(user);
    await user.click(screen.getByRole("checkbox", { name: "I will use test data only" }));
    await user.click(screen.getByRole("button", { name: "Create practice" }));

    await waitFor(() =>
      expect(requestSignup).toHaveBeenCalledWith({
        name: "Rosa Diaz",
        practice_name: "Lakeside Family Medicine",
        email: "rosa@lakeside.example.com",
        time_zone: "America/Denver",
        agreed: true,
      }),
    );
    expect(await screen.findByRole("heading", { name: "Check your email" })).toBeInTheDocument();
    expect(screen.getByText("rosa@lakeside.example.com")).toBeInTheDocument();
  });

  it("says so when self sign-up is off and still links to sign in", async () => {
    vi.mocked(getSignInProviders).mockResolvedValue({ ...TEST_DATA, signup: { ...TEST_DATA.signup, enabled: false } });
    render(<SignUpScreen />);
    expect(await screen.findByText("Self sign-up is not available.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create practice" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/sign-in");
  });
});
