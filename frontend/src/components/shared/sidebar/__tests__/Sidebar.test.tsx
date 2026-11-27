import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { SHORTCUTS } from "../../shortcuts/registry";
import { SHARED_TEXT } from "../../strings";
import { Sidebar } from "../Sidebar";
import { useSidebarCollapsed } from "../useSidebarCollapsed";

vi.mock("next/navigation", () => ({ usePathname: () => "/queue" }));
vi.mock("../useNavCounts", () => ({ useNavCounts: () => ({ queue: 7 }) }));
vi.mock("../inboxCount", () => ({ useInboxCount: (enabled: boolean) => (enabled ? 3 : undefined) }));

describe("Sidebar", () => {
  beforeEach(() => window.localStorage.clear());

  it("keeps every link named when collapsed to icons", () => {
    render(<Sidebar user={CODER} collapsed onToggle={() => undefined} onNavigate={() => undefined} />);
    expect(screen.getByRole("link", { name: /Review queue/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: SHARED_TEXT.brand })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: SHARED_TEXT.signOut })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: SHARED_TEXT.expandSidebar })).toHaveAttribute("aria-expanded", "false");
  });

  it("shows a billing-only admin the plan screen, the account and sign out, and nothing else", () => {
    const admin = { ...CODER, role: "admin" as const, billing_only: true };
    render(<Sidebar user={admin} collapsed={false} onToggle={() => undefined} onNavigate={() => undefined} />);
    const links = screen.getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual([SHARED_TEXT.brand, "Plan and billing"]);
    expect(screen.getByRole("link", { name: "Plan and billing" })).toHaveAttribute("href", "/plan");
    expect(screen.getByRole("link", { name: SHARED_TEXT.brand })).toHaveAttribute("href", "/plan");
    expect(screen.queryByRole("button", { name: "Search" })).not.toBeInTheDocument();
    expect(screen.getByText(CODER.name)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: SHARED_TEXT.signOut })).toBeInTheDocument();
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
