import { fireEvent, render, screen } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/errors";
import type { QueuePage } from "@/lib/api/types";
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

describe("QueueScreen", () => {
  beforeEach(() => {
    setSession({ access_token: "token", user: CODER });
    vi.mocked(getProviders).mockResolvedValue([]);
  });

  afterEach(() => {
    clearSession();
    vi.mocked(getQueue).mockReset();
    router.replace.mockReset();
  });

  it("shows a loading state while the queue is on its way", () => {
    vi.mocked(getQueue).mockReturnValue(new Promise<QueuePage>(() => undefined));
    render(<QueueScreen />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading notes");
  });

  it("shows the empty state when no note waits", async () => {
    vi.mocked(getQueue).mockResolvedValue(page([]));
    render(<QueueScreen />);
    expect(await screen.findByText("No notes here")).toBeInTheDocument();
  });

  it("shows the server message and retries on request", async () => {
    vi.mocked(getQueue)
      .mockRejectedValueOnce(new ApiError(503, "unavailable", "the reader is busy"))
      .mockResolvedValueOnce(page([ROW]));
    render(<QueueScreen />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The reader is busy");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("link", { name: "Marisol Reyes" })).toBeInTheDocument();
    expect(getQueue).toHaveBeenCalledTimes(2);
  });

  it("lists each note with its codes, status and the total waiting", async () => {
    vi.mocked(getQueue).mockResolvedValue(page([ROW]));
    render(<QueueScreen />);
    const link = await screen.findByRole("link", { name: "Marisol Reyes" });
    expect(link).toHaveAttribute("href", "/notes/note-1");
    expect(screen.getByText("Billed too high")).toBeInTheDocument();
    expect(screen.getByText("99215")).toBeInTheDocument();
    expect(screen.getByText("I10")).toBeInTheDocument();
    expect(screen.getByText("99214")).toBeInTheDocument();
    expect(screen.getByText("10 notes, sorted by when they're due")).toBeInTheDocument();
  });

  it("offers to read again the notes that could not be read", async () => {
    vi.mocked(getQueue).mockResolvedValue(page([ROW], 2));
    render(<QueueScreen />);
    expect(await screen.findByRole("button", { name: "Read 2 again" })).toBeInTheDocument();
    expect(screen.getByText("10 notes, sorted by when they're due")).toBeInTheDocument();
  });

  it("shows who has each note by initials, with the full name on hover", async () => {
    vi.mocked(getQueue).mockResolvedValue(page([{ ...ROW, assigned_to: "user-2", assignee_name: "Omar Haddad" }]));
    render(<QueueScreen />);
    const chip = await screen.findByTitle("Omar Haddad");
    expect(chip).toHaveTextContent("OH");
    expect(screen.getByRole("columnheader", { name: "Assigned" })).toBeInTheDocument();
  });
});
