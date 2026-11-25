import { fireEvent, render, screen } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { requestPasswordReset } from "@/lib/api/auth";
import { ForgotPasswordScreen } from "../ForgotPasswordScreen";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/api/auth", () => ({ requestPasswordReset: vi.fn() }));

function send(email: string): void {
  render(<ForgotPasswordScreen />);
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: email } });
  fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));
}

describe("ForgotPasswordScreen", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it.each(["sam@lakeside.example.com", "nobody@lakeside.example.com"])(
    "shows the same confirmation after sending for %s",
    async (email) => {
      vi.mocked(requestPasswordReset).mockResolvedValue(undefined);
      send(email);

      expect(await screen.findByText("Check your email")).toBeInTheDocument();
      expect(requestPasswordReset).toHaveBeenCalledWith(email);
      expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Back to sign in" })).toHaveAttribute("href", "/sign-in");
    },
  );

  it("asks for a valid email before sending anything", () => {
    send("not-an-email");

    expect(screen.getByText("Enter a valid email.")).toBeInTheDocument();
    expect(requestPasswordReset).not.toHaveBeenCalled();
  });
});
