import { act, render, renderHook, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { SHORTCUTS } from "../../shortcuts/registry";
import { SHARED_TEXT } from "../../strings";
import { Sidebar } from "../Sidebar";
import { useSidebarCollapsed } from "../useSidebarCollapsed";

const navigation = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ usePathname: () => "/queue", useRouter: () => navigation }));
vi.mock("../useNavCounts", () => ({ useNavCounts: () => ({ queue: 7 }) }));
vi.mock("../inboxCount", () => ({ useInboxCount: (enabled: boolean) => (enabled ? 3 : undefined) }));

describe("Sidebar", () => {
  beforeEach(() => window.localStorage.clear());

  it("keeps every link and the account menu named when collapsed to icons", () => {
    render(<Sidebar user={CODER} collapsed onToggle={() => undefined} onNavigate={() => undefined} />);
    expect(screen.getByRole("link", { name: /Review queue/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: SHARED_TEXT.brand })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Priya Nair, Coder" })).toHaveAttribute("aria-haspopup", "menu");
    expect(screen.getByRole("button", { name: SHARED_TEXT.expandSidebar })).toHaveAttribute("aria-expanded", "false");
  });

  it("gives a coder four entries and moves the account, the tour and sign out into the menu", async () => {
    render(<Sidebar user={CODER} collapsed={false} onToggle={() => undefined} onNavigate={() => undefined} />);
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual(["Today", "Inbox3", "Upload notes", "Review queue7"]);
    expect(screen.queryByRole("button", { name: SHARED_TEXT.signOut })).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Priya Nair, Coder" }));
    expect(screen.getByRole("menuitem", { name: "Take the tour" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: SHARED_TEXT.signOut })).toBeInTheDocument();
  });

  it("shows a billing-only admin the settings entry for the plan, and only sign out in the menu", async () => {
    const admin = { ...CODER, role: "admin" as const, billing_only: true };
    render(<Sidebar user={admin} collapsed={false} onToggle={() => undefined} onNavigate={() => undefined} />);
    const links = screen.getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual([SHARED_TEXT.brand, "Settings"]);
    expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("href", "/settings/plan");
    expect(screen.getByRole("link", { name: SHARED_TEXT.brand })).toHaveAttribute("href", "/settings/plan");
    expect(screen.queryByRole("button", { name: "Search" })).not.toBeInTheDocument();
    expect(screen.getByText(CODER.name)).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Priya Nair, Admin" }));
    expect(screen.getAllByRole("menuitem").map((item) => item.textContent)).toEqual([SHARED_TEXT.signOut]);
  });

  it("offers to collapse when expanded and reports the toggle", async () => {
    const onToggle = vi.fn();
    render(<Sidebar user={CODER} collapsed={false} onToggle={onToggle} onNavigate={() => undefined} />);
    const toggle = screen.getByRole("button", { name: SHARED_TEXT.collapseSidebar });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await userEvent.setup().click(toggle);
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("remembers the choice for the next visit", () => {
    const first = renderHook(() => useSidebarCollapsed());
    expect(first.result.current.collapsed).toBe(false);
    act(() => first.result.current.toggle());
    expect(first.result.current.collapsed).toBe(true);
    expect(renderHook(() => useSidebarCollapsed()).result.current.collapsed).toBe(true);
  });

  it("shows the unread inbox count beside Inbox and offers HQ search on the admin host", () => {
    const { unmount } = render(<Sidebar user={CODER} collapsed={false} onToggle={() => undefined} onNavigate={() => undefined} />);
    expect(screen.getByRole("link", { name: /Inbox/ })).toHaveAttribute("href", "/inbox");
    expect(screen.getByRole("link", { name: /Inbox/ })).toHaveTextContent("3");
    unmount();
    const hq = { ...CODER, role: "hq" as const, practice: null };
    render(<Sidebar user={hq} collapsed={false} onToggle={() => undefined} onNavigate={() => undefined} />);
    expect(screen.queryByRole("link", { name: /Inbox/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
  });

  it("registers [ as the global shortcut", () => {
    expect(SHORTCUTS.find((shortcut) => shortcut.id === "toggleSidebar")?.combos).toEqual([{ key: "[" }]);
  });
});
