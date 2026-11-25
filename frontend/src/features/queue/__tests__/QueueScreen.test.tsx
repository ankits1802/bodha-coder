import { fireEvent, render, screen } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/errors";
import type { QueuePage, QueueRow, User } from "@/lib/api/types";
import { getProviders } from "@/lib/api/uploads";
import { getQueue } from "@/lib/api/work";
import { clearSession, setSession } from "@/lib/session/store";
import { QueueScreen } from "../QueueScreen";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(""),
  usePathname: () => "/queue",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
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

const CODER: User = {
  id: "user-1",
  name: "Priya Nair",
  email: "priya.nair@example.com",
  role: "coder",
  practice: {
    id: "practice-1",
    name: "Lakeside Primary Care",
    checks: { em: true, icd: true, cdi: true, audit: true, mips: false },
    idle_minutes: 15,
    time_zone: "America/Chicago",
  },
};

const LANES: QueuePage["lanes"] = {
  approve: { total: 3, due_soon: 1 },
  coder: { total: 4, due_soon: 2 },
  provider: { total: 1, due_soon: 0 },
  compliance: { total: 2, due_soon: 0 },
};

const ROW: QueueRow = {
  id: "note-1",
  patient_name: "Marisol Reyes",
  provider_name: "Elena Varga",
  service_date: "2026-11-25",
  status: "ready",
  lane: "coder",
  lane_reason: "code_changes",
  headline: "Billed too high",
  place_code: "11",
  visit_type: "Established patient",
  flag_reason: null,
  flagged_by: null,
  due_at: "2026-11-27T18:00:00Z",
  file_name: "2026-11-25 - REYES MARISOL - 99215.pdf",
  billed: ["99215", "I10"],
  suggested: ["99214"],
  em_action: "lower",
};

function page(items: QueueRow[]): QueuePage {
  return { items, lanes: LANES, page_size: 50 };
}

describe("QueueScreen", () => {
  beforeEach(() => {
    setSession({ access_token: "token", user: CODER });
    vi.mocked(getProviders).mockResolvedValue([]);
  });

  afterEach(() => {
    clearSession();
    vi.mocked(getQueue).mockReset();
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
});
