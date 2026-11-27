import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { leavePractice, switchPractice } from "@/lib/api/auth";
import { refreshSession } from "@/lib/api/client";
import type { SignedIn, User } from "@/lib/api/types";
import { enterPractice } from "@/lib/session/practiceEntry";
import { signOut } from "@/lib/session/signOut";
import { closeOverlay, useOpenOverlay } from "../../overlays";
import { AccountMenu } from "../AccountMenu";

const navigation = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => navigation }));
vi.mock("@/lib/api/auth", () => ({ leavePractice: vi.fn(), switchPractice: vi.fn(), NEW_PRACTICE_PATH: "/practices/new" }));
vi.mock("@/lib/api/client", () => ({ refreshSession: vi.fn() }));
vi.mock("@/lib/session/signOut", () => ({ signOut: vi.fn() }));
vi.mock("@/lib/session/practiceEntry", () => ({ enterPractice: vi.fn() }));

const TWO: User = {
  ...CODER,
  practices: [
    { id: "practice-1", name: "Lakeside Primary Care", role: "coder" },
    { id: "practice-2", name: "Riverbend Clinic", role: "biller" },
  ],
};
const MENU = "Priya Nair, Coder";

function OpenOverlay() {
  return <output>{useOpenOverlay() ?? "none"}</output>;
}

async function openMenu(user: User = TWO, onNavigate = vi.fn()) {
  const events = userEvent.setup();
  render(
    <>
      <AccountMenu user={user} collapsed={false} onNavigate={onNavigate} />
      <OpenOverlay />
    </>,
  );
  await events.click(screen.getByRole("button", { name: MENU }));
  return events;
}

describe("AccountMenu", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(leavePractice).mockResolvedValue(undefined);
    vi.mocked(refreshSession).mockResolvedValue(true);
  });

  afterEach(() => closeOverlay());

  it("holds the account page, every practice with its role, leaving, a new practice, the tour and sign out", async () => {
    await openMenu();
    const menu = screen.getByRole("menu", { name: MENU });
    expect(Array.from(menu.querySelectorAll("[role^='menuitem']"), (item) => item.textContent)).toEqual([
      "Account",
      "Lakeside Primary Care · Coder",
      "Riverbend Clinic · Biller",
      "Leave Lakeside Primary Care…",
      "Leave Riverbend Clinic…",
      "New practice",
      "Take the tour",
      "Sign out",
    ]);
    expect(within(menu).getByRole("menuitemradio", { name: "Lakeside Primary Care · Coder" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("button", { name: MENU }).closest("[data-tour]")).toHaveAttribute("data-tour", "tour");
  });

  it("opens the account page and closes the phone menu", async () => {
    const onNavigate = vi.fn();
    const events = await openMenu(TWO, onNavigate);
    await events.click(screen.getByRole("menuitem", { name: "Account" }));
    expect(navigation.push).toHaveBeenCalledWith("/account");
    expect(onNavigate).toHaveBeenCalled();
  });

  it("switches to another practice from the list", async () => {
    const switched: SignedIn = { access_token: "next", user: { ...TWO, role: "biller" } };
    vi.mocked(switchPractice).mockResolvedValue(switched);
    const events = await openMenu();
    await events.click(screen.getByRole("menuitemradio", { name: "Riverbend Clinic · Biller" }));
    expect(switchPractice).toHaveBeenCalledWith("practice-2");
    await waitFor(() => expect(enterPractice).toHaveBeenCalledWith(switched));
  });

  it("leaves another practice after confirming and reloads the session", async () => {
    const events = await openMenu();
    await events.click(screen.getByRole("menuitem", { name: "Leave Riverbend Clinic…" }));
    const dialog = await screen.findByRole("dialog", { name: "Leave Riverbend Clinic?" });
    await events.click(within(dialog).getByRole("button", { name: "Leave" }));
    expect(leavePractice).toHaveBeenCalledWith("practice-2");
    await waitFor(() => expect(refreshSession).toHaveBeenCalled());
    expect(signOut).not.toHaveBeenCalled();
  });

  it("starts the tour and signs out from the menu", async () => {
    const events = await openMenu();
    await events.click(screen.getByRole("menuitem", { name: "Take the tour" }));
    expect(screen.getByRole("status")).toHaveTextContent("tour");
    await events.click(screen.getByRole("button", { name: MENU }));
    await events.click(screen.getByRole("menuitem", { name: "Sign out" }));
    expect(signOut).toHaveBeenCalled();
  });

  it("opens each organization the person runs", async () => {
    const admin: User = { ...TWO, organizations: [{ id: "org-1", name: "Acme Health", role: "admin" }] };
    const events = await openMenu(admin);
    const menu = screen.getByRole("menu", { name: MENU });
    expect(within(menu).getByRole("menuitem", { name: "Acme Health · Organization" })).toBeInTheDocument();
    await events.click(within(menu).getByRole("menuitem", { name: "Acme Health · Organization" }));
    expect(navigation.push).toHaveBeenCalledWith("/organizations/org-1");
  });

  it("offers the organization plan and sign out in a billing-only session", async () => {
    const ended: User = { ...TWO, billing_only: true, organizations: [{ id: "org-1", name: "Acme Health", role: "admin" }] };
    const events = await openMenu(ended);
    expect(screen.getAllByRole("menuitem").map((item) => item.textContent)).toEqual(["Acme Health · Organization", "Sign out"]);
    await events.click(screen.getByRole("menuitem", { name: "Acme Health · Organization" }));
    expect(navigation.push).toHaveBeenCalledWith("/organizations/org-1/plan");
  });

  it("gives an HQ account the tour and sign out only", async () => {
    const hq: User = { ...CODER, role: "hq", practice: null, practices: [] };
    const events = userEvent.setup();
    render(<AccountMenu user={hq} collapsed onNavigate={vi.fn()} />);
    await events.click(screen.getByRole("button", { name: "Priya Nair, Platform admin" }));
    expect(screen.getAllByRole("menuitem").map((item) => item.textContent)).toEqual(["Take the tour", "Sign out"]);
  });
});
