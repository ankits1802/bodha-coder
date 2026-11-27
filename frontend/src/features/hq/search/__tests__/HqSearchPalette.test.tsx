import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { closeOverlay, openOverlay } from "@/components/shared/overlays";
import { searchHq } from "@/lib/api/hq";
import type { HqSearchResults, Role, User } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";
import { HqSearchPalette } from "../HqSearchPalette";

const router = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/lib/api/hq", () => ({ searchHq: vi.fn() }));

const RESULTS: HqSearchResults = {
  practices: [{ id: "p1", name: "Lakeside Primary Care", status: "active" }],
  people: [
    {
      id: "u1",
      name: "Lara Chen",
      email: "lara@hillside.example.com",
      practices: [
        { id: "p2", name: "Hillside", role: "coder" },
        { id: "p1", name: "Lakeside Primary Care", role: "admin" },
      ],
    },
  ],
  limit: 20,
};

function signIn(role: Role): void {
  const user: User = {
    id: "user-1",
    name: "Bodha Admin",
    email: "owner@bodha.example.com",
    role,
    billing_only: false,
    practice: null,
    practices: [],
  };
  setSession({ access_token: "token", user });
}

describe("HqSearchPalette", () => {
  afterEach(() => {
    closeOverlay();
    clearSession();
    vi.mocked(searchHq).mockReset();
    router.push.mockReset();
  });

  it("opens with Ctrl+K and finds practices and people from two characters", async () => {
    signIn("hq");
    vi.mocked(searchHq).mockResolvedValue(RESULTS);
    render(<HqSearchPalette />);
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const box = await screen.findByRole("combobox", { name: "Search" });
    fireEvent.change(box, { target: { value: "l" } });
    fireEvent.change(box, { target: { value: "la" } });

    expect(await screen.findByRole("option", { name: /Lara Chen/ })).toBeInTheDocument();
    expect(searchHq).toHaveBeenCalledTimes(1);
    expect(searchHq).toHaveBeenCalledWith("la");
    expect(screen.getByRole("group", { name: "Practices" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "People" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Lara Chen/ })).toHaveTextContent("lara@hillside.example.com · Hillside · Coder");
    fireEvent.keyDown(box, { key: "Enter" });
    expect(router.push).toHaveBeenCalledWith("/hq/practices/p1");
    await waitFor(() => expect(screen.queryByRole("combobox", { name: "Search" })).not.toBeInTheDocument());
  });

  it("opens a person's first practice on its people tab", async () => {
    signIn("hq");
    vi.mocked(searchHq).mockResolvedValue(RESULTS);
    render(<HqSearchPalette />);
    act(() => openOverlay("search"));
    const box = await screen.findByRole("combobox", { name: "Search" });
    fireEvent.change(box, { target: { value: "lara@" } });
    await screen.findByRole("option", { name: /Lara Chen/ });
    fireEvent.keyDown(box, { key: "ArrowDown" });
    expect(screen.getByRole("option", { name: /Lara Chen/ })).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(box, { key: "Enter" });
    expect(router.push).toHaveBeenCalledWith("/hq/practices/p2?tab=people");
  });

  it("says when nothing matches", async () => {
    signIn("hq");
    vi.mocked(searchHq).mockResolvedValue({ practices: [], people: [], limit: 20 });
    render(<HqSearchPalette />);
    act(() => openOverlay("search"));
    fireEvent.change(await screen.findByRole("combobox", { name: "Search" }), { target: { value: "zz" } });
    expect(await screen.findByText("No practices or people found")).toBeInTheDocument();
  });

  it("is HQ only", () => {
    signIn("admin");
    render(<HqSearchPalette />);
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(screen.queryByRole("combobox", { name: "Search" })).not.toBeInTheDocument();
    expect(searchHq).not.toHaveBeenCalled();
  });
});
