import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { Role } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";
import { HelpScreen } from "../HelpScreen";

function signIn(role: Role): void {
  setSession({ access_token: "token", user: { id: "user-1", name: "Priya Nair", email: "priya@example.com", role, billing_only: false, practice: null, practices: [] } });
}

function headings(): string[] {
  return screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent ?? "");
}

describe("HelpScreen", () => {
  afterEach(() => clearSession());

  it("shows a coder the sections for their work and the shortcuts they can use", () => {
    signIn("coder");
    render(<HelpScreen />);
    expect(headings()).toEqual([
      "Upload notes",
      "Review notes",
      "Ask the provider",
      "Two-step verification and recovery codes",
      "Keyboard shortcuts",
    ]);
    expect(screen.getByText("Search notes")).toBeInTheDocument();
    expect(screen.getByText("Approve")).toBeInTheDocument();
  });

  it("shows a viewer only what applies to them", () => {
    signIn("viewer");
    render(<HelpScreen />);
    expect(headings()).toEqual(["Upload notes", "Two-step verification and recovery codes", "Keyboard shortcuts"]);
    expect(screen.getByText("Show keyboard shortcuts")).toBeInTheDocument();
    expect(screen.queryByText("Search notes")).not.toBeInTheDocument();
  });
});
