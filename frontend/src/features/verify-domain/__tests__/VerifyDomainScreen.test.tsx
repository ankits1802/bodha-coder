import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { verifyDomainLink } from "@/lib/api/domainVerification";
import { ApiError } from "@/lib/api/errors";
import { VerifyDomainScreen } from "../VerifyDomainScreen";

vi.mock("@/lib/api/domainVerification", () => ({ verifyDomainLink: vi.fn() }));

function openLink(token: string): void {
  window.history.replaceState(null, "", `/verify-domain-${token}#${token}`);
  render(<VerifyDomainScreen />);
}

describe("VerifyDomainScreen", () => {
  beforeEach(() => vi.resetAllMocks());

  it("confirms the domain only when the person presses the button", async () => {
    vi.mocked(verifyDomainLink).mockResolvedValue({ domain: "lakeside.example.com", practice_name: "Lakeside Primary Care" });
    openLink("domain-1");
    expect(verifyDomainLink).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", { name: "Confirm domain" }));
    expect(verifyDomainLink).toHaveBeenCalledWith("domain-1");
    expect(await screen.findByText("lakeside.example.com is confirmed for Lakeside Primary Care")).toBeInTheDocument();
  });

  it("shows why a link was not accepted", async () => {
    vi.mocked(verifyDomainLink).mockRejectedValue(new ApiError(401, "unauthorized", "this link has expired"));
    openLink("domain-2");
    await userEvent.setup().click(screen.getByRole("button", { name: "Confirm domain" }));
    expect(await screen.findByText("This link has expired")).toBeInTheDocument();
  });

  it("says when the link carries no token", () => {
    window.history.replaceState(null, "", "/verify-domain-empty");
    render(<VerifyDomainScreen />);
    expect(screen.getByText("This link has expired.")).toBeInTheDocument();
  });
});
