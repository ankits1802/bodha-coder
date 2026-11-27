import { fireEvent, render, screen, within } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { QueueViews } from "@/lib/api/types";
import { getProviders } from "@/lib/api/uploads";
import { getQueue, getQueueViews } from "@/lib/api/work";
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
  voidNotes: vi.fn(),
  remindProvider: vi.fn(),
  reopenNotes: vi.fn(),
  retryFailedNotes: vi.fn(),
}));

const PLAIN = { lane: null, reason: null, assigned: null, provider_id: null, overdue: false, sort: "due" } as const;
const VIEWS: QueueViews = {
  builtin: [{ key: "my_work", filters: { ...PLAIN, assigned: "me" } }],
  saved: [{ id: "view-1", name: "Big changes", filters: { ...PLAIN, lane: "coder", sort: "impact" } }],
};
const SECOND = { ...ROW, id: "note-2", patient_name: "Omar Haddad" };

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
  router.replace.mockReset();
  search.value = "";
});

describe("the provider lane split", () => {
  it("shows questions to send apart from notes waiting on the provider", async () => {
    render(<QueueScreen />);
    const lanes = await screen.findByRole("radiogroup", { name: "Show notes" });
    expect(within(lanes).getByRole("radio", { name: /^Questions to send/ })).toHaveTextContent("1");
    expect(within(lanes).getByRole("radio", { name: /^Waiting on provider/ })).toHaveTextContent("0");
    fireEvent.click(within(lanes).getByRole("radio", { name: /^Questions to send/ }));
    expect(router.replace).toHaveBeenLastCalledWith("/queue?lane=provider&reason=questions", { scroll: false });
  });

  it("asks the server for the reason and clears it for a lane without one", async () => {
    search.value = "lane=provider&reason=waiting_on_provider";
    render(<QueueScreen />);
    const lanes = await screen.findByRole("radiogroup", { name: "Show notes" });
    expect(within(lanes).getByRole("radio", { name: /^Waiting on provider/ })).toHaveAttribute("aria-checked", "true");
    expect(getQueue).toHaveBeenCalledWith(expect.objectContaining({ lane: "provider", reason: "waiting_on_provider" }));
    fireEvent.click(within(lanes).getByRole("radio", { name: /^Needs a coder/ }));
    expect(router.replace).toHaveBeenLastCalledWith("/queue?lane=coder", { scroll: false });
  });
});

describe("sorting by dollar impact", () => {
  it("sorts on request and shows each note's estimated change", async () => {
    render(<QueueScreen />);
    await screen.findByRole("link", { name: "Marisol Reyes" });
    fireEvent.click(screen.getByRole("combobox", { name: "Sort" }));
    fireEvent.click(screen.getByRole("option", { name: "Dollar impact" }));
    expect(router.replace).toHaveBeenLastCalledWith("/queue?sort=impact", { scroll: false });
  });

  it("asks for the impact order and says so", async () => {
    search.value = "sort=impact";
    render(<QueueScreen />);
    expect(await screen.findByText("10 notes, sorted by dollar impact")).toBeInTheDocument();
    expect(getQueue).toHaveBeenCalledWith(expect.objectContaining({ sort: "impact" }));
    expect(screen.getByText(/\$42\.11/)).toBeInTheDocument();
  });
});

describe("queue keys", () => {
  it("selects with X, the focused row first, and assigns the selection with A", async () => {
    vi.mocked(getQueue).mockResolvedValue(page([ROW, SECOND]));
    render(<QueueScreen />);
    const second = await screen.findByRole("link", { name: "Omar Haddad" });
    second.focus();
    fireEvent.keyDown(second, { key: "x" });
    expect(screen.getByRole("checkbox", { name: "Select Omar Haddad" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Select Marisol Reyes" })).not.toBeChecked();
    second.blur();
    fireEvent.keyDown(window, { key: "x" });
    expect(screen.getByRole("checkbox", { name: "Select Marisol Reyes" })).toBeChecked();
    fireEvent.keyDown(window, { key: "a" });
    expect(await screen.findByRole("heading", { name: "Assign 2 notes" })).toBeInTheDocument();
  });

  it("does nothing on A while nothing is selected", async () => {
    render(<QueueScreen />);
    await screen.findByRole("link", { name: "Marisol Reyes" });
    fireEvent.keyDown(window, { key: "a" });
    expect(screen.queryByRole("heading", { name: /Assign/ })).not.toBeInTheDocument();
  });
});
