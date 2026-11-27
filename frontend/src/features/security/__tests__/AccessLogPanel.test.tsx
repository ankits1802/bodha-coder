import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { exportAccessLog, getAccessLog } from "@/lib/api/practice";
import type { AccessLogPage, User } from "@/lib/api/types";
import { saveFile } from "@/lib/download";
import { clearSession, setSession } from "@/lib/session/store";
import { AccessLogPanel } from "../AccessLogPanel";

const router = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn() }));
const search = vi.hoisted(() => ({ value: "" }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(search.value),
  usePathname: () => "/insights/access-log",
  useRouter: () => router,
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
vi.mock("@/lib/api/practice", () => ({ getAccessLog: vi.fn(), exportAccessLog: vi.fn() }));
vi.mock("@/lib/download", () => ({ saveFile: vi.fn() }));

const COMPLIANCE: User = {
  id: "user-9",
  name: "Jordan Diaz",
  email: "jordan@lakeside.example.com",
  role: "compliance",
  billing_only: false,
  practice: {
    id: "practice-1",
    name: "Lakeside Primary Care",
    checks: { em: true, icd: true, cdi: true, audit: true, mips: false, hcc: false },
    can_send_texts: true,
    idle_minutes: 15,
    time_zone: "America/Chicago",
  },
  practices: [],
};

const PAGE: AccessLogPage = {
  items: [
    {
      at: "2026-11-20T15:00:00Z",
      actor: "Priya Nair",
      actor_kind: "user",
      action: "opened note",
      note_id: "note-1",
      detail: null,
      ip: "203.0.113.7",
      user_agent: null,
    },
  ],
  total: 1,
  offset: 0,
  page_size: 200,
  people: [{ id: "user-3", name: "Priya Nair" }],
  actions: ["opened note", "signed in"],
};

const FILTERS = {
  start: "2026-11-01",
  end: "2026-11-27",
  user_id: null,
  action: "opened note",
  note_id: null,
  patient: "Reyes",
  birth_date: null,
};

describe("AccessLogPanel", () => {
  beforeEach(() => {
    setSession({ access_token: "token", user: COMPLIANCE });
    search.value = "start=2026-11-01&end=2026-11-27&action=opened+note&patient=Reyes";
    vi.mocked(getAccessLog).mockResolvedValue(PAGE);
  });

  afterEach(() => {
    clearSession();
    vi.resetAllMocks();
  });

  it("asks for the filtered entries and exports them with the same filters", async () => {
    const blob = new Blob(["at,actor"], { type: "text/csv" });
    vi.mocked(exportAccessLog).mockResolvedValue({ blob, fileName: "bodha-access-log-20261128-1500.csv" });
    render(<AccessLogPanel />);

    expect(await screen.findByText("Priya Nair")).toBeInTheDocument();
    expect(getAccessLog).toHaveBeenCalledWith(FILTERS, 0);
    expect(screen.getByRole("combobox", { name: "Person" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Export" }));

    await waitFor(() => expect(exportAccessLog).toHaveBeenCalledWith(FILTERS));
    await waitFor(() => expect(saveFile).toHaveBeenCalledWith(blob, "bodha-access-log-20261128-1500.csv"));
  });

  it("applies a typed note ID when Enter is pressed and goes back to the first page", async () => {
    render(<AccessLogPanel />);
    await screen.findByText("Priya Nair");
    const note = screen.getByRole("searchbox", { name: "Note ID" });

    fireEvent.change(note, { target: { value: "note-1" } });
    expect(router.replace).not.toHaveBeenCalled();
    fireEvent.keyDown(note, { key: "Enter" });

    expect(router.replace).toHaveBeenCalledWith(
      "/insights/access-log?start=2026-11-01&end=2026-11-27&action=opened+note&patient=Reyes&note=note-1",
      { scroll: false },
    );
  });
});
