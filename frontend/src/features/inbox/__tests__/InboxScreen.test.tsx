import { fireEvent, render, screen, within } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { announceInboxCount } from "@/components/shared/sidebar/inboxCount";
import { CODER } from "@/features/queue/__tests__/fixtures";
import { getInbox, markAllInboxRead, markInboxRead } from "@/lib/api/inbox";
import { clearSession, setSession } from "@/lib/session/store";
import { InboxScreen } from "../InboxScreen";
import { inboxEntry, inboxPage } from "./inboxFixtures";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(""),
  usePathname: () => "/inbox",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/api/inbox", () => ({ getInbox: vi.fn(), markInboxRead: vi.fn(), markAllInboxRead: vi.fn() }));
vi.mock("@/components/shared/sidebar/inboxCount", () => ({ announceInboxCount: vi.fn() }));

const ANSWERED = inboxEntry({ id: "item-1", kind: "provider_answered", payload: { questions: 3 } });
const MENTION = inboxEntry({
  id: "item-2",
  kind: "mentioned",
  actor_name: "Priya Nair",
  payload: { comment_id: "c-1", on: "finding" },
  read_at: "2026-11-27T16:00:00Z",
});

describe("InboxScreen", () => {
  beforeEach(() => setSession({ access_token: "token", user: CODER }));

  afterEach(() => {
    clearSession();
    vi.mocked(getInbox).mockReset();
    vi.mocked(markInboxRead).mockReset();
    vi.mocked(markAllInboxRead).mockReset();
    vi.mocked(announceInboxCount).mockReset();
  });

  it("lists unread items first with an unread marker and tells the sidebar the count", async () => {
    vi.mocked(getInbox).mockResolvedValue(inboxPage([ANSWERED, MENTION], 1));
    render(<InboxScreen />);
    const list = await screen.findByRole("list", { name: "Inbox items" });
    const links = within(list).getAllByRole("link");
    expect(links[0]).toHaveTextContent("Unread: Elena Varga answered 3 questions");
    expect(links[0]).toHaveTextContent("Marisol Reyes · 25 Nov");
    expect(links[0]).toHaveAttribute("href", "/notes/note-1");
    expect(links[1]).toHaveTextContent("Priya Nair mentioned you");
    expect(links[1]).not.toHaveTextContent("Unread");
    expect(links[1]).toHaveAttribute("href", "/notes/note-1?tab=history");
    expect(screen.getByText("1 unread")).toBeInTheDocument();
    expect(announceInboxCount).toHaveBeenCalledWith(1);
    expect(getInbox).toHaveBeenCalledWith(0);
  });

  it("marks an unread item read when it is opened, and leaves read ones alone", async () => {
    vi.mocked(getInbox).mockResolvedValue(inboxPage([ANSWERED, MENTION], 1));
    vi.mocked(markInboxRead).mockResolvedValue({ unread: 0 });
    render(<InboxScreen />);
    fireEvent.click(await screen.findByRole("link", { name: /answered 3 questions/ }));
    expect(markInboxRead).toHaveBeenCalledWith(["item-1"]);
    await vi.waitFor(() => expect(announceInboxCount).toHaveBeenLastCalledWith(0));
    fireEvent.click(screen.getByRole("link", { name: /mentioned you/ }));
    expect(markInboxRead).toHaveBeenCalledTimes(1);
  });

  it("marks everything read and reloads", async () => {
    vi.mocked(getInbox).mockResolvedValueOnce(inboxPage([ANSWERED], 1)).mockResolvedValueOnce(inboxPage([{ ...ANSWERED, read_at: "now" }], 0));
    vi.mocked(markAllInboxRead).mockResolvedValue({ unread: 0 });
    render(<InboxScreen />);
    fireEvent.click(await screen.findByRole("button", { name: "Mark all read" }));
    await vi.waitFor(() => expect(getInbox).toHaveBeenCalledTimes(2));
    expect(markAllInboxRead).toHaveBeenCalledTimes(1);
    expect(announceInboxCount).toHaveBeenCalledWith(0);
    await vi.waitFor(() => expect(screen.getByRole("button", { name: "Mark all read" })).toBeDisabled());
  });

  it("shows the empty state when nothing came in", async () => {
    vi.mocked(getInbox).mockResolvedValue(inboxPage([], 0));
    render(<InboxScreen />);
    expect(await screen.findByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mark all read" })).toBeDisabled();
  });
});
