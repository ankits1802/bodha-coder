import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/errors";
import { chooseJoin, getJoinPage } from "@/lib/api/signupJoin";
import type { JoinPage } from "@/lib/api/types";
import { JoinScreen } from "../JoinScreen";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/api/signupJoin", () => ({ getJoinPage: vi.fn(), chooseJoin: vi.fn() }));

const PAGE: JoinPage = {
  email: "dana@lakeside.example.com",
  name: "Dana Fox",
  own_practice_name: "Harbor Kids",
  join: { practice_name: "Lakeside Primary Care", mode: "auto" },
};

function openLink(token: string): void {
  window.history.replaceState(null, "", `/sign-up/join-${token}#${token}`);
  render(<JoinScreen />);
}

describe("JoinScreen", () => {
  beforeEach(() => vi.resetAllMocks());

  it("joins the practice that holds the email domain", async () => {
    vi.mocked(getJoinPage).mockResolvedValue(PAGE);
    vi.mocked(chooseJoin).mockResolvedValue({ outcome: "joined" });
    openLink("join-1");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Join Lakeside Primary Care" }));
    expect(chooseJoin).toHaveBeenCalledWith({ token: "join-1", join: true });
    expect(await screen.findByText("Check your email")).toBeInTheDocument();
    expect(getJoinPage).toHaveBeenCalledWith("join-1");
  });

  it("asks to join when the practice reviews requests", async () => {
    vi.mocked(getJoinPage).mockResolvedValue({ ...PAGE, join: { practice_name: "Lakeside Primary Care", mode: "request" } });
    vi.mocked(chooseJoin).mockResolvedValue({ outcome: "requested" });
    openLink("join-2");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Ask to join Lakeside Primary Care" }));
    expect(await screen.findByText("Request sent to Lakeside Primary Care")).toBeInTheDocument();
  });

  it("starts the person's own practice instead", async () => {
    vi.mocked(getJoinPage).mockResolvedValue(PAGE);
    vi.mocked(chooseJoin).mockResolvedValue({ outcome: "started" });
    openLink("join-3");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Start Harbor Kids" }));
    expect(chooseJoin).toHaveBeenCalledWith({ token: "join-3", join: false });
    expect(await screen.findByText("Check your email")).toBeInTheDocument();
  });

  it("offers only a new practice once no practice takes the domain", async () => {
    vi.mocked(getJoinPage).mockResolvedValue({ ...PAGE, join: null });
    openLink("join-4");
    expect(await screen.findByRole("button", { name: "Start Harbor Kids" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Join/ })).not.toBeInTheDocument();
  });

  it("shows the refusal beside the choices", async () => {
    vi.mocked(getJoinPage).mockResolvedValue(PAGE);
    vi.mocked(chooseJoin).mockRejectedValue(new ApiError(409, "conflict", "this email already has an account; sign in instead"));
    openLink("join-5");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Join Lakeside Primary Care" }));
    expect(await screen.findByText("this email already has an account; sign in instead")).toBeInTheDocument();
  });

  it("says when the link has expired", async () => {
    vi.mocked(getJoinPage).mockRejectedValue(new ApiError(401, "unauthorized", "this link has expired; start sign-up again"));
    openLink("join-6");
    await waitFor(() => expect(screen.getByText("This link has expired.")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "Start again" })).toHaveAttribute("href", "/sign-up");
  });
});
