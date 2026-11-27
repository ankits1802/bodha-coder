import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { closeOverlay, openOverlay } from "@/components/shared/overlays";
import { searchNotes } from "@/lib/api/search";
import type { NoteSummary, Role, User } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";
import { SearchPalette } from "../SearchPalette";

const router = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/lib/api/search", () => ({ searchNotes: vi.fn() }));

function signIn(role: Role, { billingOnly = false }: { billingOnly?: boolean } = {}): void {
  const user: User = {
    id: "user-1",
    name: "Priya Nair",
    email: "priya.nair@example.com",
    role,
    billing_only: billingOnly,
    practice: {
      id: "practice-1",
      name: "Lakeside Primary Care",
      checks: { em: true, icd: true, cdi: true, audit: true, mips: false, hcc: false },
      idle_minutes: 15,
      time_zone: "America/Chicago",
    },
  };
  setSession({ access_token: "token", user });
}

function note(id: string, patient: string, status: NoteSummary["status"]): NoteSummary {
  return {
    id,
    patient_name: patient,
    provider_name: "Elena Varga",
    service_date: "2026-11-25",
    status,
    lane: null,
    lane_reason: null,
    headline: null,
    place_code: "11",
    visit_type: "Established patient",
    flag_reason: null,
    flagged_by: null,
    due_at: "2026-11-28T06:00:00Z",
    file_name: `${patient}.pdf`,
    assigned_to: null,
    payer: null,
  };
}

describe("SearchPalette", () => {
  afterEach(() => {
    closeOverlay();
    clearSession();
    vi.mocked(searchNotes).mockReset();
    router.push.mockReset();
  });

  it("opens with Ctrl+K, searches from two characters and opens the chosen note from the keyboard", async () => {
    signIn("coder");
    vi.mocked(searchNotes).mockResolvedValue({
      items: [note("note-1", "Reyes Marisol", "ready"), note("note-2", "Reyes Tomas", "exported")],
      limit: 50,
    });
    render(<SearchPalette />);
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const box = await screen.findByRole("combobox", { name: "Search" });
    fireEvent.change(box, { target: { value: "r" } });
    fireEvent.change(box, { target: { value: "re" } });

    expect(await screen.findByRole("option", { name: /Reyes Tomas/ })).toBeInTheDocument();
    expect(searchNotes).toHaveBeenCalledTimes(1);
    expect(searchNotes).toHaveBeenCalledWith("re");
    expect(screen.getByText("Exported")).toBeInTheDocument();
    fireEvent.keyDown(box, { key: "ArrowDown" });
    expect(screen.getByRole("option", { name: /Reyes Tomas/ })).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(box, { key: "Enter" });
    expect(router.push).toHaveBeenCalledWith("/notes/note-2");
    await waitFor(() => expect(screen.queryByRole("combobox", { name: "Search" })).not.toBeInTheDocument());
  });

  it("opens with the slash key but not while typing in a field", async () => {
    signIn("biller");
    render(
      <>
        <input aria-label="Other field" />
        <SearchPalette />
      </>,
    );
    fireEvent.keyDown(screen.getByRole("textbox", { name: "Other field" }), { key: "/" });
    expect(screen.queryByRole("combobox", { name: "Search" })).not.toBeInTheDocument();
    fireEvent.keyDown(window, { key: "/" });
    expect(await screen.findByRole("combobox", { name: "Search" })).toBeInTheDocument();
  });

  it("shows when no note matches", async () => {
    signIn("admin");
    vi.mocked(searchNotes).mockResolvedValue({ items: [], limit: 50 });
    render(<SearchPalette />);
    act(() => openOverlay("search"));
    fireEvent.change(await screen.findByRole("combobox", { name: "Search" }), { target: { value: "zz" } });
    expect(await screen.findByText("No notes found")).toBeInTheDocument();
  });

  it("is not offered to a role that cannot read notes", () => {
    signIn("viewer");
    render(<SearchPalette />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(screen.queryByRole("combobox", { name: "Search" })).not.toBeInTheDocument();
  });

  it("is not offered to an admin whose plan has ended", () => {
    signIn("admin", { billingOnly: true });
    render(<SearchPalette />);
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(screen.queryByRole("combobox", { name: "Search" })).not.toBeInTheDocument();
    expect(searchNotes).not.toHaveBeenCalled();
  });
});
