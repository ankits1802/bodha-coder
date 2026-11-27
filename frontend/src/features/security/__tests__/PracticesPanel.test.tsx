import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { leavePractice } from "@/lib/api/auth";
import { refreshSession } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { User } from "@/lib/api/types";
import { signOut } from "@/lib/session/signOut";
import { PracticesPanel } from "../PracticesPanel";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
vi.mock("@/lib/api/auth", () => ({ leavePractice: vi.fn(), NEW_PRACTICE_PATH: "/practices/new" }));
vi.mock("@/lib/api/client", () => ({ refreshSession: vi.fn() }));
vi.mock("@/lib/session/signOut", () => ({ signOut: vi.fn() }));

const PERSON: User = {
  ...CODER,
  practices: [
    { id: "practice-1", name: "Lakeside Primary Care", role: "coder" },
    { id: "practice-2", name: "Riverbend Clinic", role: "admin" },
  ],
};

async function leave(name: string): Promise<void> {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: `Leave ${name}` }));
  const dialog = await screen.findByRole("dialog", { name: `Leave ${name}?` });
  await user.click(within(dialog).getByRole("button", { name: "Leave" }));
}

describe("PracticesPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(leavePractice).mockResolvedValue(undefined);
    vi.mocked(refreshSession).mockResolvedValue(true);
  });

  it("lists each practice with the person's role and marks the current one", () => {
    render(<PracticesPanel user={PERSON} />);
    const items = within(screen.getByRole("list", { name: "Your practices" })).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "Lakeside Primary CareCoder · This practiceLeave",
      "Riverbend ClinicAdminLeave",
    ]);
    expect(screen.getByRole("link", { name: "New practice" })).toHaveAttribute("href", "/practices/new");
  });

  it("leaves another practice and reloads the session", async () => {
    render(<PracticesPanel user={PERSON} />);
    await leave("Riverbend Clinic");
    expect(leavePractice).toHaveBeenCalledWith("practice-2");
    await waitFor(() => expect(refreshSession).toHaveBeenCalled());
    expect(signOut).not.toHaveBeenCalled();
  });

  it("signs out after leaving the practice the session is in", async () => {
    render(<PracticesPanel user={PERSON} />);
    await leave("Lakeside Primary Care");
    expect(leavePractice).toHaveBeenCalledWith("practice-1");
    await waitFor(() => expect(signOut).toHaveBeenCalled());
  });

  it("keeps the dialog open with the reason when the last admin may not leave", async () => {
    vi.mocked(leavePractice).mockRejectedValue(new ApiError(409, "conflict", "a practice needs at least one active admin"));
    render(<PracticesPanel user={PERSON} />);
    await leave("Riverbend Clinic");
    const dialog = screen.getByRole("dialog", { name: "Leave Riverbend Clinic?" });
    expect(await within(dialog).findByText(/at least one active admin/i)).toBeInTheDocument();
    expect(refreshSession).not.toHaveBeenCalled();
  });
});
