import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { assignNotes, deleteNotes } from "@/lib/api/notes";
import { getProviders } from "@/lib/api/uploads";
import { getQueue } from "@/lib/api/work";
import { clearSession, setSession } from "@/lib/session/store";
import { QueueScreen } from "../QueueScreen";
import { CODER, page, ROW } from "./fixtures";

const router = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn() }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(""),
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

vi.mock("@/lib/api/work", () => ({ getQueue: vi.fn() }));
vi.mock("@/lib/api/uploads", () => ({ getProviders: vi.fn() }));
vi.mock("@/lib/api/notes", () => ({
  approveNotes: vi.fn(),
  assignNotes: vi.fn(),
  deleteNotes: vi.fn(),
  remindProvider: vi.fn(),
  retryFailedNotes: vi.fn(),
}));

describe("queue assignment and bulk actions", () => {
  beforeEach(() => {
    setSession({ access_token: "token", user: CODER });
    vi.mocked(getProviders).mockResolvedValue([]);
    vi.mocked(getQueue).mockResolvedValue(page([ROW]));
  });

  afterEach(() => {
    clearSession();
    vi.mocked(getQueue).mockReset();
    router.replace.mockReset();
  });

  it("filters to my notes from the menu and with the M key", async () => {
    render(<QueueScreen />);
    await screen.findByRole("link", { name: "Marisol Reyes" });
    fireEvent.change(screen.getByRole("combobox", { name: "Assigned" }), { target: { value: "me" } });
    expect(router.replace).toHaveBeenLastCalledWith("/queue?assigned=me", { scroll: false });
    router.replace.mockClear();
    fireEvent.keyDown(window, { key: "m" });
    expect(router.replace).toHaveBeenLastCalledWith("/queue?assigned=me", { scroll: false });
  });

  it("assigns the selected notes to the coder", async () => {
    vi.mocked(assignNotes).mockResolvedValue({ assigned: ["note-1"] });
    render(<QueueScreen />);
    fireEvent.click(await screen.findByRole("checkbox", { name: "Select Marisol Reyes" }));
    fireEvent.click(screen.getByRole("button", { name: "Assign to…" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Person" }), { target: { value: "user-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Assign" }));
    await waitFor(() => expect(assignNotes).toHaveBeenCalledWith(["note-1"], "user-1"));
    expect(await screen.findByText("1 assigned")).toBeInTheDocument();
  });

  it("deletes the selected notes after a confirmation that names the count", async () => {
    vi.mocked(deleteNotes).mockResolvedValue({ deleted: ["note-1"] });
    render(<QueueScreen />);
    fireEvent.click(await screen.findByRole("checkbox", { name: "Select Marisol Reyes" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete 1" }));
    expect(screen.getByRole("heading", { name: "Delete 1 note?" })).toBeInTheDocument();
    expect(deleteNotes).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Delete 1 note" }));
    await waitFor(() => expect(deleteNotes).toHaveBeenCalledWith(["note-1"]));
    expect(await screen.findByText("1 deleted")).toBeInTheDocument();
  });
});
