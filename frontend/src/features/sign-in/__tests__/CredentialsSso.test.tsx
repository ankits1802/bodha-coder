import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { discoverSso } from "@/lib/api/sso";
import { CredentialsForm } from "../CredentialsForm";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/api/sso", () => ({ discoverSso: vi.fn() }));

const START = "/api/auth/saml/c-1/start";

function renderForm() {
  const onSubmit = vi.fn();
  const onSingleSignOn = vi.fn();
  render(<CredentialsForm pending={false} error={null} onSubmit={onSubmit} onSingleSignOn={onSingleSignOn} />);
  return { onSubmit, onSingleSignOn };
}

function typeEmail(email: string): void {
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: email } });
}

describe("CredentialsForm with single sign-on", () => {
  beforeEach(() => vi.mocked(discoverSso).mockReset());

  it("sends a domain that requires single sign-on to the identity provider", async () => {
    vi.mocked(discoverSso).mockResolvedValue({ mode: "required", start_url: START });
    const { onSubmit, onSingleSignOn } = renderForm();
    typeEmail("anna@lakeside.example.com");

    const button = await screen.findByRole("button", { name: "Continue with single sign-on" });
    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
    fireEvent.click(button);

    expect(onSingleSignOn).toHaveBeenCalledWith(START);
    expect(onSubmit).not.toHaveBeenCalled();
    expect(discoverSso).toHaveBeenCalledWith("anna@lakeside.example.com");
  });

  it("lets a break-glass admin use a password instead", async () => {
    vi.mocked(discoverSso).mockResolvedValue({ mode: "required", start_url: START });
    const { onSubmit } = renderForm();
    typeEmail("admin@lakeside.example.com");
    fireEvent.click(await screen.findByRole("button", { name: "Use a password" }));

    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-horse-staple" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(onSubmit).toHaveBeenCalledWith("admin@lakeside.example.com", "correct-horse-staple");
  });

  it("offers single sign-on beside the password when it is optional", async () => {
    vi.mocked(discoverSso).mockResolvedValue({ mode: "optional", start_url: START });
    const { onSingleSignOn } = renderForm();
    typeEmail("anna@lakeside.example.com");

    fireEvent.click(await screen.findByRole("button", { name: "Continue with single sign-on" }));

    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(onSingleSignOn).toHaveBeenCalledWith(START);
  });

  it("keeps the password form when the domain has no single sign-on or the address is incomplete", async () => {
    vi.mocked(discoverSso).mockResolvedValue({ mode: "none", start_url: null });
    renderForm();
    typeEmail("anna@");
    typeEmail("someone@gmail.com");

    await waitFor(() => expect(discoverSso).toHaveBeenCalledTimes(1));
    expect(discoverSso).toHaveBeenCalledWith("someone@gmail.com");
    expect(screen.queryByRole("button", { name: "Continue with single sign-on" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });
});
