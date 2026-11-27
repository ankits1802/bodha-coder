import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { switchPractice } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/errors";
import type { SignedIn, User } from "@/lib/api/types";
import { enterPractice } from "@/lib/session/practiceEntry";
import { Sidebar } from "../Sidebar";

vi.mock("next/navigation", () => ({ usePathname: () => "/queue", useRouter: () => ({ push: vi.fn() }) }));
vi.mock("../useNavCounts", () => ({ useNavCounts: () => ({ queue: 0 }) }));
vi.mock("@/lib/api/auth", () => ({ switchPractice: vi.fn() }));
vi.mock("@/lib/session/practiceEntry", () => ({ enterPractice: vi.fn() }));

const TWO: User = {
  ...CODER,
  practices: [
    { id: "practice-1", name: "Lakeside Primary Care", role: "coder" },
    { id: "practice-2", name: "Riverbend Clinic", role: "biller" },
  ],
};
const SWITCHED: SignedIn = { access_token: "next", user: { ...TWO, role: "biller" } };
const LABEL = "Practice: Lakeside Primary Care";

function show(user: User, collapsed = false): void {
  render(<Sidebar user={user} collapsed={collapsed} onToggle={() => undefined} onNavigate={() => undefined} />);
}

describe("PracticeSwitcher", () => {
  beforeEach(() => vi.resetAllMocks());

  it("stays out of the way for a person with one practice", () => {
    show(CODER);
    expect(screen.queryByRole("button", { name: LABEL })).not.toBeInTheDocument();
    expect(screen.getByText("Lakeside Primary Care")).toBeInTheDocument();
  });

  it("lists every practice with the current one marked", async () => {
    show(TWO);
    await userEvent.setup().click(screen.getByRole("button", { name: LABEL }));
    const menu = screen.getByRole("menu", { name: LABEL });
    const choices = within(menu).getAllByRole("menuitemradio");
    expect(choices.map((choice) => choice.textContent)).toEqual(["Lakeside Primary Care", "Riverbend Clinic"]);
    expect(choices[0]).toHaveAttribute("aria-checked", "true");
    expect(choices[1]).toHaveAttribute("aria-checked", "false");
    expect(choices[0]).toHaveFocus();
  });

  it("switches from the keyboard and opens the other practice", async () => {
    vi.mocked(switchPractice).mockResolvedValue(SWITCHED);
    const user = userEvent.setup();
    show(TWO);
    screen.getByRole("button", { name: LABEL }).focus();
    await user.keyboard("{Enter}");
    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitemradio", { name: "Riverbend Clinic" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(switchPractice).toHaveBeenCalledWith("practice-2");
    await waitFor(() => expect(enterPractice).toHaveBeenCalledWith(SWITCHED));
  });

  it("does nothing when the current practice is chosen again", async () => {
    const user = userEvent.setup();
    show(TWO);
    await user.click(screen.getByRole("button", { name: LABEL }));
    await user.click(screen.getByRole("menuitemradio", { name: "Lakeside Primary Care" }));
    expect(switchPractice).not.toHaveBeenCalled();
  });

  it("works with the sidebar collapsed and says why a switch failed", async () => {
    vi.mocked(switchPractice).mockRejectedValue(new ApiError(403, "forbidden", "you are not an active member of that practice"));
    const user = userEvent.setup();
    show(TWO, true);
    await user.click(screen.getByRole("button", { name: LABEL }));
    await user.click(screen.getByRole("menuitemradio", { name: "Riverbend Clinic" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/not an active member of that practice/i);
    expect(enterPractice).not.toHaveBeenCalled();
  });
});
