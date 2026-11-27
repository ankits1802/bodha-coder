import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/errors";
import type { QueueViews } from "@/lib/api/types";
import { getProviders } from "@/lib/api/uploads";
import { deleteQueueView, getQueue, getQueueViews, saveQueueView } from "@/lib/api/work";
import { clearSession, setSession } from "@/lib/session/store";
import { QueueScreen } from "../QueueScreen";
import { CODER, page, ROW } from "./fixtures";

const router = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn() }));
const search = vi.hoisted(() => ({ value: "" }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(search.value),
  usePathname: () => "/queue",
  useRouter: () => router,
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
vi.mock("@/lib/api/work", () => ({ getQueue: vi.fn(), getQueueViews: vi.fn(), saveQueueView: vi.fn(), deleteQueueView: vi.fn() }));
vi.mock("@/lib/api/uploads", () => ({ getProviders: vi.fn() }));
vi.mock("@/lib/api/notes", () => ({
  approveNotes: vi.fn(),
  assignNotes: vi.fn(),
  deleteNotes: vi.fn(),
  remindProvider: vi.fn(),
  reopenNotes: vi.fn(),
  retryFailedNotes: vi.fn(),
}));

const PLAIN = { lane: null, reason: null, assigned: null, provider_id: null, overdue: false, sort: "due" } as const;
const VIEWS: QueueViews = {
  builtin: [{ key: "my_work", filters: { ...PLAIN, assigned: "me" } }],
  saved: [{ id: "view-1", name: "Big changes", filters: { ...PLAIN, lane: "coder", sort: "impact" } }],
};

beforeEach(() => {
  window.localStorage.clear();
  setSession({ access_token: "token", user: CODER });
  vi.mocked(getProviders).mockResolvedValue([]);
  vi.mocked(getQueue).mockResolvedValue(page([ROW]));
  vi.mocked(getQueueViews).mockResolvedValue(VIEWS);
});

afterEach(() => {
  clearSession();
  vi.mocked(getQueue).mockReset();
  vi.mocked(getQueueViews).mockReset();
  vi.mocked(saveQueueView).mockReset();
  router.replace.mockReset();
  search.value = "";
});

describe("queue views", () => {
  it("applies a built-in or saved view and marks the one in use", async () => {
    search.value = "assigned=me";
    render(<QueueScreen />);
    const views = await screen.findByRole("radiogroup", { name: "Views" });
    expect(within(views).getByRole("radio", { name: "My work" })).toHaveAttribute("aria-checked", "true");
    fireEvent.click(within(views).getByRole("radio", { name: "Big changes" }));
    expect(router.replace).toHaveBeenLastCalledWith("/queue?lane=coder&sort=impact", { scroll: false });
  });

  it("saves the current filters under a name and shows a refusal inline", async () => {
    search.value = "assigned=me&overdue=1";
    vi.mocked(saveQueueView)
      .mockRejectedValueOnce(new ApiError(409, "conflict", "you already have a view with that name"))
      .mockResolvedValueOnce({ id: "view-2", name: "Late", filters: { ...PLAIN, assigned: "me", overdue: true } });
    render(<QueueScreen />);
    fireEvent.click(await screen.findByRole("button", { name: "Save view" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Name" }), { target: { value: "Late" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("You already have a view with that name")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(saveQueueView).toHaveBeenLastCalledWith({ name: "Late", filters: { ...PLAIN, assigned: "me", overdue: true } }));
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Save this view" })).not.toBeInTheDocument());
    expect(getQueueViews).toHaveBeenCalledTimes(2);
  });

  it("deletes a saved view", async () => {
    vi.mocked(deleteQueueView).mockResolvedValue(undefined);
    render(<QueueScreen />);
    fireEvent.click(await screen.findByRole("button", { name: "Saved views" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete Big changes" }));
    await waitFor(() => expect(deleteQueueView).toHaveBeenCalledWith("view-1"));
  });
});
